"""
Overview-bezogene Views: Request, Export, ScheduledExport, MovementReport.
"""
from datetime import datetime, timedelta
import json
import os
from types import SimpleNamespace
from django.utils import timezone
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import FileResponse, JsonResponse
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum, Prefetch
from django import forms
from django.conf import settings

from ..forms import (
    ScheduledExportForm,
)
from ..models import (
    InventoryItem,
    InventoryHistory,
    Category,
    UserProfile,
    BorrowedItem,
    TagType,
    ApplicationTag,
    StorageLocation,
    Overview,
    ScheduledExport,
    ExportRun,
    ItemMark,
)
from ..exports import EXPORT_COLUMNS, calculate_next_run, export_overview_to_file
from ..pdf_export import export_overview_to_pdf
from .helpers import _get_overview_and_features, _feature_enabled


# ---------------------------------------------------------------------------
# Overview-Request-Form (inline in views.py war)
# ---------------------------------------------------------------------------
class OverviewRequestForm(forms.ModelForm):
    """Formular für Dashboard-Anfrage – alle möglichen Optionen."""

    slug = forms.SlugField(
        required=False,
        max_length=80,
        label="Slug (URL-Kürzel)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "z. B. werkstatt"}),
        help_text="Optional – wird automatisch erzeugt, wenn leer.",
    )

    def _unique_slug(self, base: str) -> str:
        base_slug = (slugify(base) or "dashboard")[:80].strip("-") or "dashboard"
        slug = base_slug
        suffix = 2
        qs = Overview.objects.all()
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        while qs.filter(slug=slug).exists():
            suffix_text = f"-{suffix}"
            slug = f"{base_slug[:80 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return slug

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        name = self.cleaned_data.get("name") or ""
        if not slug:
            return self._unique_slug(name)
        slug = slugify(slug)
        qs = Overview.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Dieser Slug ist bereits vergeben.")
        return slug

    def save(self, commit=True):
        overview = super().save(commit=False)
        if not overview.slug:
            overview.slug = self._unique_slug(overview.name)
        if commit:
            overview.save()
            self.save_m2m()
        return overview

    class Meta:
        model = Overview
        fields = [
            "name",
            "slug",
            "icon_emoji",
            "description",
            "categories",
            "show_quantity",
            "has_locations",
            "has_min_stock",
            "enable_borrow",
            "is_consumable_mode",
            "require_qr",
            "enable_quick_adjust",
            "show_images",
            "show_tags",
            "enable_mark_button",
            "enable_advanced_filters",
            "enable_comments",
            "show_order_button",
        ]
        labels = {
            "name": "Dashboard-Name",
            "slug": "Slug (URL-Kürzel)",
            "icon_emoji": "Icon (Emoji)",
            "description": "Beschreibung",
            "categories": "Kategorien",
            "show_quantity": "Mengen anzeigen",
            "has_locations": "Lagerorte verwenden",
            "has_min_stock": "Mindestbestand verwenden",
            "enable_borrow": "Verleih/Return verwenden",
            "is_consumable_mode": "Verbrauchsmaterial-Logik",
            "require_qr": "QR/Barcode Pflicht",
            "enable_quick_adjust": "Schnellbestand +/- erlauben",
            "show_images": "Bilder anzeigen",
            "show_tags": "Tags anzeigen",
            "enable_mark_button": "Markieren-Button anzeigen",
            "enable_advanced_filters": "Erweiterte Suche/Filter",
            "enable_comments": "Kommentare/Feedback erlauben",
            "show_order_button": "Nachbestellen-Button anzeigen",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "z. B. Werkstatt, Keller, Garage"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "z. B. werkstatt"}),
            "icon_emoji": forms.TextInput(attrs={"class": "form-control", "placeholder": "z. B. 🔧"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categories": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "name": "Wähle einen aussagekräftigen Namen für dein neues Dashboard.",
            "slug": "Optional – wird automatisch erzeugt, wenn leer.",
            "icon_emoji": "Ein einzelnes Emoji als Icon.",
        }


class OverviewRequestCreateView(LoginRequiredMixin, View):
    template_name = "inventory/overview_request_form.html"

    def get(self, request):
        form = OverviewRequestForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = OverviewRequestForm(request.POST)
        if form.is_valid():
            overview = form.save(commit=False)
            overview.is_active = False
            overview.requested_by = request.user
            overview.save()
            # M2M-Felder speichern (v. a. categories)
            form.save_m2m()
            messages.success(
                request,
                "Dein Dashboard wurde angefragt. Ein Admin wird es freischalten.",
            )
            return redirect("dashboards")
        return render(request, self.template_name, {"form": form})


# ---------------------------------------------------------------------------
# Export Views
# ---------------------------------------------------------------------------
class OverviewExportView(LoginRequiredMixin, View):
    def get(self, request, slug, export_format):
        overview = get_object_or_404(Overview, slug=slug, is_active=True)
        selected_columns = request.GET.getlist("cols") or None

        if export_format in {"csv", "excel"}:
            result = export_overview_to_file(
                overview,
                export_format=export_format,
                columns=selected_columns,
            )
            if isinstance(result, dict) and "error" in result:
                messages.error(request, f"Export fehlgeschlagen: {result['error']}")
                return redirect("overview-dashboard", slug=slug)
            full_path = os.path.join(settings.MEDIA_ROOT, result)
            filename = result.split("/")[-1]
            if not os.path.exists(full_path):
                messages.error(request, "Export-Datei wurde nicht gefunden.")
                return redirect("overview-dashboard", slug=slug)
            content_type = "text/csv; charset=utf-8"
            if export_format == "excel":
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return FileResponse(open(full_path, "rb"), as_attachment=True, filename=filename, content_type=content_type)

        if export_format == "pdf":
            export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"overview_{overview.slug}_{timestamp}.pdf"
            full_path = os.path.join(export_dir, filename)
            export_overview_to_pdf(overview, selected_columns, full_path)
            if not os.path.exists(full_path):
                messages.error(request, "PDF-Export-Datei wurde nicht gefunden.")
                return redirect("overview-dashboard", slug=slug)
            return FileResponse(open(full_path, "rb"), as_attachment=True, filename=filename, content_type="application/pdf")

        messages.error(request, "Unbekanntes Export-Format.")
        return redirect("overview-dashboard", slug=slug)


class ScheduledExportView(LoginRequiredMixin, View):
    template_name = "inventory/scheduled_exports.html"

    def get(self, request):
        exports = ScheduledExport.objects.select_related("overview").order_by("overview__name")
        runs = ExportRun.objects.select_related("scheduled_export").order_by("-created_at")[:20]
        return render(request, self.template_name, {
            "exports": exports, "runs": runs,
            "export_columns": [(key, label) for key, label, _ in EXPORT_COLUMNS],
            "form": ScheduledExportForm(),
        })

    def post(self, request):
        post_data = request.POST.copy()
        post_data["columns"] = json.dumps(request.POST.getlist("cols"))
        form = ScheduledExportForm(post_data)
        if form.is_valid():
            form.save()
            messages.success(request, "Geplanter Export wurde angelegt.")
            return redirect("scheduled-exports")
        exports = ScheduledExport.objects.select_related("overview").order_by("overview__name")
        runs = ExportRun.objects.select_related("scheduled_export").order_by("-created_at")[:20]
        return render(request, self.template_name, {
            "exports": exports, "runs": runs,
            "export_columns": [(key, label) for key, label, _ in EXPORT_COLUMNS],
            "form": form,
        })


class ScheduledExportRunView(LoginRequiredMixin, View):
    def post(self, request, pk):
        export = get_object_or_404(ScheduledExport, pk=pk)
        try:
            result = export_overview_to_file(
                overview=export.overview,
                export_format=export.export_format,
                columns=export.columns,
            )
            if isinstance(result, dict):
                raise RuntimeError(result.get("error") or "Export fehlgeschlagen")
            ExportRun.objects.create(
                scheduled_export=export,
                status=ExportRun.Status.SUCCESS,
                file_path=result,
            )
            export.last_run_at = timezone.now()
            export.next_run_at = calculate_next_run(export.frequency, export.last_run_at)
            export.save(update_fields=["last_run_at", "next_run_at"])
            messages.success(request, f"Export „{export.overview.name}“ erfolgreich ausgeführt.")
        except Exception as exc:
            ExportRun.objects.create(
                scheduled_export=export,
                status=ExportRun.Status.FAILED,
                error_message=str(exc),
            )
            messages.error(request, f"Export fehlgeschlagen: {exc}")
        return redirect("scheduled-exports")


# ---------------------------------------------------------------------------
# Movement Report
# ---------------------------------------------------------------------------
class MovementReportView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/movement_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        days = self.request.GET.get("days", 7)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 7
        days = max(1, min(days, 365))
        ctx["days"] = days

        action = self.request.GET.get("action", "")
        ctx["selected_action"] = action

        since = timezone.now() - timedelta(days=days)
        qs = InventoryHistory.objects.filter(created_at__gte=since).select_related("item", "user")

        if action:
            qs = qs.filter(action=action)

        ctx["movements"] = qs.order_by("-created_at")
        ctx["actions"] = InventoryHistory.Action.choices
        ctx["breadcrumbs"] = [
            {"name": "Dashboards", "url": reverse("dashboards")},
            {"name": "📊 Bewegungs-Report", "url": None},
        ]
        return ctx


__all__ = [
    "OverviewRequestForm",
    "OverviewRequestCreateView",
    "OverviewExportView",
    "ScheduledExportView",
    "ScheduledExportRunView",
    "MovementReportView",
]
