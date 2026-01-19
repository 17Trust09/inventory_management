# inventory/admin_views.py

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

# NEU: wir brauchen den User für die Bearbeitungs-/Löschmaske
from django.contrib.auth.models import User

# (Barcode/QR werden anderswo evtl. genutzt – Imports belassen)
from barcode import Code128
from barcode.writer import ImageWriter
import qrcode
import uuid
import subprocess
import shutil

from .feature_flags import get_feature_flags
from .models import (
    InventoryItem,
    InventoryHistory,
    BorrowedItem,
    ApplicationTag,
    TagType,
    Category,
    UserProfile,
    GlobalSettings,
    StorageLocation,
    Overview,
    Feedback,
)
from .forms import StorageLocationForm

# ============================================================
# Zugriffsschutz: Nur Admins (is_staff ODER is_superuser)
# ============================================================

def _is_staff_or_super(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def _is_superuser(user):
    return user.is_authenticated and user.is_superuser

def staff_required(view_func):
    """Decorator für FBVs: lässt nur is_staff/is_superuser rein."""
    return user_passes_test(_is_staff_or_super, login_url="login")(view_func)

def superuser_required(view_func):
    """Decorator für FBVs: lässt nur Superuser rein."""
    return user_passes_test(_is_superuser, login_url="login")(view_func)

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin für CBVs: lässt nur is_staff/is_superuser rein."""
    def test_func(self):
        return _is_staff_or_super(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Kein Zugriff. Bitte als Admin anmelden.")
        return redirect("login")

class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin für CBVs: lässt nur Superuser rein."""
    def test_func(self):
        return _is_superuser(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Kein Zugriff. Bitte als Superuser anmelden.")
        return redirect("login")


def _feature_enabled(flag_name: str) -> bool:
    return get_feature_flags().get(flag_name, True)

# ---------------------------------------------------------------------
# FORMS
# ---------------------------------------------------------------------
class ApplicationTagForm(forms.ModelForm):
    class Meta:
        model = ApplicationTag
        fields = ['name']  # nur globale Tags
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
        }
        labels = {'name': 'Tag-Name'}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = self.fields['name'].widget.attrs.get('class', '')
        if 'form-control' not in css:
            self.fields['name'].widget.attrs['class'] = (css + ' form-control form-control-lg').strip()


# ---------------------------------------------------------------------
# Admin-Dashboard
# ---------------------------------------------------------------------
@staff_required
def dashboard(request):
    """
    Admin-Dashboard mit Schnellüberblick.
    Letzte Feedbacks + Quick-Actions.
    """
    latest_feedback = Feedback.objects.select_related("created_by").order_by("-created_at")[:8]
    return render(request, 'inventory/admin_dashboard.html', {
        "latest_feedback": latest_feedback
    })


# ---------------------------------------------------------------------
# Kategorien & Tags – Übersichten
# ---------------------------------------------------------------------
@staff_required
def admin_categories_overview(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/admin_categories_overview.html', {
        'categories': categories,
    })


@staff_required
def admin_tags_overview(request):
    tags = ApplicationTag.objects.order_by('name')
    return render(request, 'inventory/admin_tags_overview.html', {
        'tags': tags,
    })


# ---------------------------------------------------------------------
# Historie & Rollback (Admin)
# ---------------------------------------------------------------------
@staff_required
def admin_history_list(request):
    if not _feature_enabled("show_admin_history"):
        messages.error(request, "Historie & Rollback sind aktuell deaktiviert.")
        return redirect("admin_dashboard")
    action = (request.GET.get("action") or "").strip()
    user_id = (request.GET.get("user") or "").strip()
    query = (request.GET.get("q") or "").strip()

    history = InventoryHistory.objects.select_related("item", "user").order_by("-created_at")
    if action:
        history = history.filter(action=action)
    if user_id:
        history = history.filter(user_id=user_id)
    if query:
        history = history.filter(item__name__icontains=query)

    users = User.objects.filter(inventory_history_entries__isnull=False).distinct().order_by("username")

    return render(
        request,
        "inventory/admin_history_list.html",
        {
            "history_entries": history[:200],
            "action_choices": InventoryHistory.Action.choices,
            "selected_action": action,
            "selected_user": user_id,
            "selected_query": query,
            "users": users,
        },
    )


@staff_required
def admin_history_rollback(request, pk):
    if not _feature_enabled("show_admin_history"):
        messages.error(request, "Historie & Rollback sind aktuell deaktiviert.")
        return redirect("admin_dashboard")
    if request.method != "post" and request.method != "POST":
        return HttpResponseBadRequest("Ungültige Methode.")

    history = get_object_or_404(InventoryHistory, pk=pk)
    if not history.data_before:
        messages.error(request, "Kein Rollback-Zustand vorhanden.")
        return redirect("admin_history_list")

    item = history.item
    current = {
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "category_id": item.category_id,
        "storage_location_id": item.storage_location_id,
        "location_letter": item.location_letter,
        "location_number": item.location_number,
        "location_shelf": item.location_shelf,
        "low_quantity": item.low_quantity,
        "order_link": item.order_link,
        "maintenance_date": item.maintenance_date,
        "overview_id": item.overview_id,
        "item_type": item.item_type,
        "is_active": item.is_active,
        "tags": list(item.application_tags.values_list("id", flat=True)),
    }
    target = history.data_before

    item.name = target.get("name")
    item.description = target.get("description")
    item.quantity = target.get("quantity") or 0
    item.category_id = target.get("category_id")
    item.storage_location_id = target.get("storage_location_id")
    item.location_letter = target.get("location_letter")
    item.location_number = target.get("location_number")
    item.location_shelf = target.get("location_shelf")
    item.low_quantity = target.get("low_quantity") or 0
    item.order_link = target.get("order_link")
    maintenance_date = target.get("maintenance_date")
    if maintenance_date:
        try:
            item.maintenance_date = timezone.datetime.fromisoformat(maintenance_date).date()
        except ValueError:
            item.maintenance_date = None
    else:
        item.maintenance_date = None
    item.overview_id = target.get("overview_id")
    item.item_type = target.get("item_type") or item.item_type
    item.is_active = target.get("is_active", item.is_active)
    item.save()

    if "tags" in target:
        item.application_tags.set(target["tags"])

    InventoryHistory.objects.create(
        item=item,
        user=request.user,
        action=InventoryHistory.Action.ROLLBACK,
        data_before=current,
        data_after=target,
        changes=[],
        meta={"source_history_id": history.id, "source": "admin"},
    )

    messages.success(request, "Rollback durchgeführt.")
    return redirect("admin_history_list")


# ---------------------------------------------------------------------
# Rollen & Rechte – STILLGELEGT
# ---------------------------------------------------------------------
@staff_required
def permissions_matrix(request):
    messages.info(request, "Die Rollen-/Rechteverwaltung ist deaktiviert. Alle eingeloggten Nutzer sehen alles.")
    return redirect('admin_dashboard')


@staff_required
def toggle_permission(request):
    messages.info(request, "Die Rollen-/Rechteverwaltung ist deaktiviert.")
    return JsonResponse({'status': 'disabled'})


@staff_required
def admin_manage_roles(request):
    messages.info(request, "Die Rollenverwaltung ist deaktiviert.")
    return redirect('admin_dashboard')


@staff_required
def admin_user_roles_edit(request, pk):
    messages.info(request, "Die Rollenverwaltung ist deaktiviert.")
    return redirect('admin_dashboard')


@staff_required
def admin_user_delete_legacy(request, pk):
    messages.info(request, "Die Benutzerverwaltung über diese Seite ist deaktiviert.")
    return redirect('admin_dashboard')


# ---------------------------------------------------------------------
# KATEGORIEN – CRUD
# ---------------------------------------------------------------------
class CategoryListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/admin_categories_list.html'
    context_object_name = 'categories'


class CategoryCreateView(StaffRequiredMixin, CreateView):
    form_class = CategoryForm
    template_name = 'inventory/admin_category_form.html'

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, f"Kategorie „{obj.name}“ angelegt.")
        return redirect('admin_categories')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pool_name'] = 'Alle Kategorien'
        return ctx


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    form_class = CategoryForm
    template_name = 'inventory/admin_category_form.html'
    model = Category

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, f"Kategorie „{obj.name}“ gespeichert.")
        return redirect('admin_categories')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pool_name'] = 'Alle Kategorien'
        return ctx


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/admin_category_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Kategorie „{obj.name}“ gelöscht.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('admin_categories')


# ---------------------------------------------------------------------
# TAGS – CRUD
# ---------------------------------------------------------------------
class ApplicationTagCreateView(StaffRequiredMixin, CreateView):
    model = ApplicationTag
    form_class = ApplicationTagForm
    template_name = 'inventory/admin_tag_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ angelegt.")
        return reverse('admin_tags_overview')


class ApplicationTagUpdateView(StaffRequiredMixin, UpdateView):
    model = ApplicationTag
    form_class = ApplicationTagForm
    template_name = 'inventory/admin_tag_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ gespeichert.")
        return reverse('admin_tags_overview')


class ApplicationTagDeleteView(StaffRequiredMixin, DeleteView):
    model = ApplicationTag
    template_name = 'inventory/admin_tag_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ gelöscht.")
        return reverse('admin_tags_overview')


# ---------------------------------------------------------------------
# InventoryItem – List & Redirects
# ---------------------------------------------------------------------
class InventoryItemListView(StaffRequiredMixin, ListView):
    model = InventoryItem
    template_name = 'inventory/admin_items_list.html'
    context_object_name = 'items'


@staff_required
def admin_item_edit(request, pk):
    return redirect('edit-item', pk=pk)


@staff_required
def admin_item_delete(request, pk):
    return redirect('delete-item', pk=pk)


# ---------------------------------------------------------------------
# BorrowedItem List
# ---------------------------------------------------------------------
class BorrowedItemListView(StaffRequiredMixin, ListView):
    model = BorrowedItem
    template_name = 'inventory/admin_borrowed_items_list.html'
    context_object_name = 'borrowed_items'


# ---------------------------------------------------------------------
# UserProfile – PRO USER sichtbare Dashboards + Konto-Aktionen
# ---------------------------------------------------------------------
def _ensure_profile(user: User) -> UserProfile:
    """Sorgt dafür, dass ein UserProfile existiert (lazy creation)."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@staff_required
def admin_userprofile_edit(request, pk):
    """
    Benutzerprofiledit:
    - Overviews an-/abwählen
    - Rolle setzen (Admin/User)  -> setzt user.is_staff
    - Konto deaktivieren/reaktivieren
    - Benutzer löschen (nur wenn keine Items) oder Transfer & Löschen
    """
    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
    edit_user = profile.user

    # POST: Aktionen
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # Overviews speichern
        if action == "save_overviews":
            ids = request.POST.getlist("allowed_overviews")
            profile.allowed_overviews.set(Overview.objects.filter(pk__in=ids))
            profile.save()
            messages.success(request, "Zugriff auf Dashboards gespeichert.")
            return redirect("admin_userprofile_edit", pk=pk)

        # Rolle speichern (Admin/User)
        if action == "save_role":
            desired = (request.POST.get("role") or "").lower()
            if edit_user.is_superuser:
                messages.info(request, "Die Rolle eines Superusers kann hier nicht geändert werden.")
                return redirect("admin_userprofile_edit", pk=pk)
            if desired not in {"admin", "user"}:
                messages.error(request, "Ungültige Rollenangabe.")
                return redirect("admin_userprofile_edit", pk=pk)

            edit_user.is_staff = (desired == "admin")
            edit_user.save(update_fields=["is_staff"])
            messages.success(
                request,
                f"Rolle gespeichert: „{edit_user.username}“ ist jetzt {'Admin' if edit_user.is_staff else 'User'}."
            )
            return redirect("admin_userprofile_edit", pk=pk)

        # De-/Reaktivieren
        if action == "deactivate":
            edit_user.is_active = False
            edit_user.save(update_fields=["is_active"])
            messages.success(request, f"Benutzer „{edit_user.username}“ wurde deaktiviert.")
            return redirect("admin_userprofile_edit", pk=pk)

        if action == "reactivate":
            edit_user.is_active = True
            edit_user.save(update_fields=["is_active"])
            messages.success(request, f"Benutzer „{edit_user.username}“ wurde reaktiviert.")
            return redirect("admin_userprofile_edit", pk=pk)

        # Nur löschen (wenn keine Items)
        if action == "delete":
            items_count = InventoryItem.objects.filter(user=edit_user).count()
            if items_count > 0:
                messages.error(
                    request,
                    "Löschen nicht möglich: Dem Benutzer sind noch Artikel zugeordnet. "
                    "Bitte vorher übertragen oder löschen."
                )
                return redirect("admin_userprofile_edit", pk=pk)
            username = edit_user.username
            edit_user.delete()
            messages.success(request, f"Benutzer „{username}“ wurde gelöscht.")
            return redirect("admin_user_profiles")

        # Übertragen & löschen
        if action == "transfer_and_delete":
            target_id = request.POST.get("transfer_to")
            try:
                target = User.objects.get(pk=target_id)
            except User.DoesNotExist:
                messages.error(request, "Zielbenutzer nicht gefunden.")
                return redirect("admin_userprofile_edit", pk=pk)

            if target.pk == edit_user.pk:
                messages.error(request, "Zielbenutzer darf nicht identisch mit dem Quellbenutzer sein.")
                return redirect("admin_userprofile_edit", pk=pk)

            moved = InventoryItem.objects.filter(user=edit_user).update(user=target)
            username = edit_user.username
            edit_user.delete()
            messages.success(
                request,
                f"{moved} Artikel übertragen. Benutzer „{username}“ wurde gelöscht."
            )
            return redirect("admin_user_profiles")

        # Fallback
        messages.error(request, "Unbekannte Aktion.")
        return redirect("admin_userprofile_edit", pk=pk)

    # GET: Seite rendern
    all_overviews = Overview.objects.all().order_by("order", "name")
    current_ids = set(profile.allowed_overviews.values_list("id", flat=True))

    items_count = InventoryItem.objects.filter(user=edit_user).count()
    other_users = User.objects.exclude(pk=edit_user.pk).order_by("username")

    return render(
        request,
        "inventory/admin_userprofiles_edit.html",
        {
            "profile": profile,
            "edit_user": edit_user,
            "all_overviews": all_overviews,
            "current_ids": current_ids,
            "items_count": items_count,
            "other_users": other_users,
        },
    )


@staff_required
def admin_user_toggle_active(request, pk):
    """Aktiviere/Deaktiviere einen User-Account."""
    if request.method != "POST":
        return HttpResponseBadRequest("Nur POST erlaubt.")
    user = get_object_or_404(User, pk=pk)

    if request.user.id == user.id and request.POST.get("active") == "0":
        messages.error(request, "Du kannst dein eigenes Konto nicht deaktivieren.")
        return redirect('admin_userprofile_edit', pk=pk)

    make_active = request.POST.get("active") == "1"
    user.is_active = make_active
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        f"Benutzer „{user.username}“ wurde {'aktiviert' if make_active else 'deaktiviert'}."
    )
    return redirect('admin_userprofile_edit', pk=pk)


@staff_required
def admin_userprofile_delete(request, pk):
    """
    Löscht einen User-Account sicher:
    - verhindert Self-Delete
    - verhindert Löschen, wenn noch InventoryItems dem User gehören
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Nur POST erlaubt.")
    user = get_object_or_404(User, pk=pk)

    if request.user.id == user.id:
        messages.error(request, "Du kannst dein eigenes Konto nicht löschen.")
        return redirect('admin_userprofile_edit', pk=pk)

    if InventoryItem.objects.filter(user=user).exists():
        messages.error(
            request,
            "Löschen abgebrochen: Dem Benutzer sind noch Inventar-Artikel zugeordnet. "
            "Bitte Artikel umhängen oder löschen."
        )
        return redirect('admin_userprofile_edit', pk=pk)

    username = user.username
    user.delete()
    messages.success(request, f"Benutzer „{username}“ wurde gelöscht.")
    return redirect('admin_user_profiles')


class UserProfileListView(StaffRequiredMixin, ListView):
    model = UserProfile
    template_name = 'inventory/admin_userprofiles_list.html'
    context_object_name = 'profiles'


# ---------------------------------------------------------------------
# TagType CRUD (optional)
# ---------------------------------------------------------------------
class TagTypeListView(StaffRequiredMixin, ListView):
    model = TagType
    template_name = 'inventory/admin_tagtypes_list.html'
    context_object_name = 'tag_types'


class TagTypeCreateView(StaffRequiredMixin, CreateView):
    model = TagType
    fields = ['name']
    template_name = 'inventory/admin_tagtype_form.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ angelegt.")
        return reverse('admin_tagtypes')


class TagTypeUpdateView(StaffRequiredMixin, UpdateView):
    model = TagType
    fields = ['name']
    template_name = 'inventory/admin_tagtype_form.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ gespeichert.")
        return reverse('admin_tagtypes')


class TagTypeDeleteView(StaffRequiredMixin, DeleteView):
    model = TagType
    template_name = 'inventory/admin_tagtype_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ gelöscht.")
        return reverse('admin_tagtypes')


# ---------------------------------------------------------------------
# GlobalSettings
# ---------------------------------------------------------------------
class GlobalSettingsListView(StaffRequiredMixin, ListView):
    model = GlobalSettings
    template_name = 'inventory/admin_globalsettings_list.html'
    context_object_name = 'settings'

    def get_queryset(self):
        qs = super().get_queryset()
        if not qs.exists():
            GlobalSettings.objects.create()
            qs = super().get_queryset()
        return qs


@staff_required
def admin_globalsettings_edit(request, pk):
    gs = get_object_or_404(GlobalSettings, pk=pk)

    class GSForm(forms.ModelForm):
        class Meta:
            model = GlobalSettings
            fields = ['qr_base_url', 'nfc_base_url_local', 'nfc_base_url_remote']
            widgets = {
                'qr_base_url': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'nfc_base_url_local': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'nfc_base_url_remote': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            }
            labels = {
                'qr_base_url': 'Basis-URL für QR-Code-Links',
                'nfc_base_url_local': 'NFC-Basis-URL (Lokal)',
                'nfc_base_url_remote': 'NFC-Basis-URL (Tailscale/Remote)',
            }
            help_texts = {
                'qr_base_url': 'z. B. http://192.168.178.20:8000',
                'nfc_base_url_local': 'z. B. http://192.168.178.20:8000',
                'nfc_base_url_remote': 'z. B. https://host.tailnet-xyz.ts.net',
            }

    if request.method == 'POST':
        form = GSForm(request.POST, instance=gs)
        if form.is_valid():
            form.save()
            messages.success(request, "Globale Einstellungen gespeichert.")
            return redirect('admin_global_settings')
    else:
        form = GSForm(instance=gs)

    return render(request, 'inventory/admin_globalsettings_form.html', {'form': form})


@superuser_required
def admin_feature_toggles(request):
    settings = GlobalSettings.objects.first()
    if not settings:
        settings = GlobalSettings.objects.create()

    class FeatureToggleForm(forms.ModelForm):
        class Meta:
            model = GlobalSettings
            fields = [
                "show_patch_notes",
                "show_feedback",
                "show_movement_report",
                "show_admin_history",
                "show_scheduled_exports",
                "show_mark_button",
                "show_favorites",
                "enable_bulk_actions",
                "enable_item_move",
                "enable_item_history",
                "enable_attachments",
                "enable_image_upload",
                "enable_image_library",
                "enable_qr_actions",
                "enable_nfc_fields",
            ]
            widgets = {
                "show_patch_notes": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_feedback": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_movement_report": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_admin_history": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_scheduled_exports": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_mark_button": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "show_favorites": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_bulk_actions": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_item_move": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_item_history": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_attachments": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_image_upload": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_image_library": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_qr_actions": forms.CheckboxInput(attrs={"class": "form-check-input"}),
                "enable_nfc_fields": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            }
            labels = {
                "show_patch_notes": "Patch Notes",
                "show_feedback": "Feedback-Board",
                "show_movement_report": "Lagerbewegungen",
                "show_admin_history": "Historie & Rollback (Admin)",
                "show_scheduled_exports": "Geplante Exporte",
                "show_mark_button": "Markieren-Button im Dashboard",
                "show_favorites": "Favoriten & Schnellzugriff",
                "enable_bulk_actions": "Bulk-Aktionen",
                "enable_item_move": "Item in anderes Dashboard verschieben",
                "enable_item_history": "Verlauf & Timeline im Item-Edit",
                "enable_attachments": "Dokumente/Bilder (Anhänge)",
                "enable_image_upload": "Bild-Upload",
                "enable_image_library": "Bild-Bibliothek",
                "enable_qr_actions": "QR-Aktionen",
                "enable_nfc_fields": "NFC-Felder",
            }

    if request.method == "POST":
        form = FeatureToggleForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Feature-Schalter wurden gespeichert.")
            return redirect("admin_feature_toggles")
    else:
        form = FeatureToggleForm(instance=settings)

    return render(request, "inventory/admin_feature_toggles.html", {"form": form})


def _get_git_status(branch: str) -> dict[str, str | int]:
    base_dir = settings.BASE_DIR
    fetch = subprocess.run(
        ["git", "fetch", "origin", branch],
        cwd=base_dir,
        capture_output=True,
        text=True,
    )
    if fetch.returncode != 0:
        return {
            "branch": branch,
            "error": fetch.stderr.strip() or fetch.stdout.strip() or "Git fetch fehlgeschlagen.",
        }

    rev_list = subprocess.run(
        ["git", "rev-list", "--count", f"{branch}..origin/{branch}"],
        cwd=base_dir,
        capture_output=True,
        text=True,
    )
    if rev_list.returncode != 0:
        return {
            "branch": branch,
            "error": rev_list.stderr.strip() or rev_list.stdout.strip() or "Git-Status konnte nicht ermittelt werden.",
        }

    try:
        behind_count = int(rev_list.stdout.strip())
    except ValueError:
        behind_count = 0

    return {
        "branch": branch,
        "behind_count": behind_count,
    }


def _get_backup_entries() -> list[dict[str, str]]:
    backup_root = settings.BASE_DIR / "backup"
    if not backup_root.exists():
        return []
    entries = []
    for item in sorted(backup_root.iterdir(), reverse=True):
        if not item.is_dir():
            continue
        db_path = item / "db.sqlite3"
        media_path = item / "media"
        entries.append(
            {
                "name": item.name,
                "path": str(item),
                "has_db": db_path.exists(),
                "has_media": media_path.exists(),
            }
        )
    return entries


def _restore_backup(backup_dir: str) -> tuple[bool, str]:
    backup_path = settings.BASE_DIR / "backup" / backup_dir
    if not backup_path.exists():
        return False, "Backup-Verzeichnis nicht gefunden."

    db_source = backup_path / "db.sqlite3"
    media_source = backup_path / "media"
    if not db_source.exists():
        return False, "Backup enthält keine db.sqlite3."
    if not media_source.exists():
        return False, "Backup enthält keinen media-Ordner."

    db_target = settings.BASE_DIR / "db.sqlite3"
    media_target = settings.BASE_DIR / "media"

    try:
        shutil.copy2(db_source, db_target)
        if media_target.exists():
            shutil.rmtree(media_target)
        shutil.copytree(media_source, media_target)
    except OSError as exc:
        return False, f"Rollback fehlgeschlagen: {exc}"

    return True, "Rollback abgeschlossen."


@superuser_required
def admin_updates(request):
    update_output = None
    update_error = None
    update_branch = None
    rollback_message = None
    rollback_error = None

    if request.method == "POST":
        if request.POST.get("action") == "rollback":
            backup_dir = request.POST.get("backup_dir")
            if not backup_dir:
                messages.error(request, "Kein Backup ausgewählt.")
                return redirect("admin_updates")
            success, message = _restore_backup(backup_dir)
            if success:
                rollback_message = message
                messages.success(request, message)
            else:
                rollback_error = message
                messages.error(request, message)
            return redirect("admin_updates")

        update_branch = request.POST.get("branch")
        if update_branch not in {"main", "dev"}:
            messages.error(request, "Ungültiger Branch für das Update.")
            return redirect("admin_updates")

        status = _get_git_status(update_branch)
        if status.get("error"):
            messages.error(request, f"Update-Check fehlgeschlagen: {status['error']}")
            return redirect("admin_updates")

        if status.get("behind_count", 0) == 0:
            messages.info(request, f"{update_branch} ist bereits aktuell.")
            return redirect("admin_updates")

        script_path = settings.BASE_DIR / f"update_from_{update_branch}.sh"
        if not script_path.exists():
            messages.error(request, f"Update-Skript fehlt: {script_path}")
            return redirect("admin_updates")

        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
        )
        update_output = (result.stdout or "").strip()
        update_error = (result.stderr or "").strip()
        if result.returncode == 0:
            messages.success(request, f"Update von {update_branch} gestartet.")
        else:
            messages.error(request, f"Update von {update_branch} fehlgeschlagen (Exit-Code {result.returncode}).")

    context = {
        "status_main": _get_git_status("main"),
        "status_dev": _get_git_status("dev"),
        "update_output": update_output,
        "update_error": update_error,
        "update_branch": update_branch,
        "backup_entries": _get_backup_entries(),
        "rollback_message": rollback_message,
        "rollback_error": rollback_error,
    }
    return render(request, "inventory/admin_updates.html", context)


# ---------------------------------------------------------------------
# QR-Code Overview
# ---------------------------------------------------------------------
@staff_required
def admin_qr_codes_view(request):
    items = InventoryItem.objects.all()
    return render(request, 'inventory/admin_qr_overview.html', {'items': items})


# ---------------------------------------------------------------------
# Storage Locations
# ---------------------------------------------------------------------
class StorageLocationListView(StaffRequiredMixin, ListView):
    model = StorageLocation
    template_name = 'inventory/admin_storagelocations_list.html'
    context_object_name = 'locations'

    def get_queryset(self):
        qs = super().get_queryset()
        return sorted(qs, key=lambda loc: loc.get_full_path().lower())


class StorageLocationCreateView(StaffRequiredMixin, CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/admin_storagelocation_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["parent_tree"] = ctx["form"].parent_tree()
        ctx["parent_selected"] = ctx["form"].instance.parent_id
        ctx["is_create"] = True
        ctx["nfc_url"] = ""
        return ctx

    def get_success_url(self):
        messages.success(self.request, f"Lagerort „{self.object.name}“ wurde erstellt.")
        return reverse('admin_storagelocations')


class StorageLocationUpdateView(StaffRequiredMixin, UpdateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/admin_storagelocation_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["parent_tree"] = ctx["form"].parent_tree()
        ctx["parent_selected"] = ctx["form"].instance.parent_id
        ctx["is_create"] = False
        if self.object.nfc_token:
            gs = GlobalSettings.objects.first()
            local_base = gs.nfc_base_url_local if gs else ""
            remote_base = gs.nfc_base_url_remote if gs else ""
            base = local_base if self.object.nfc_base_choice == "local" else remote_base
            if not base:
                base = self.request.build_absolute_uri("/").rstrip("/")
            ctx["nfc_url"] = (
                f"{base.rstrip('/')}{reverse('nfc-location-redirect', kwargs={'token': self.object.nfc_token})}"
            )
        else:
            ctx["nfc_url"] = ""
        return ctx

    def get_success_url(self):
        messages.success(self.request, f"Lagerort „{self.object.name}“ wurde gespeichert.")
        return reverse('admin_storagelocations')


class StorageLocationDeleteView(StaffRequiredMixin, DeleteView):
    model = StorageLocation
    template_name = 'inventory/admin_storagelocation_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"Lagerort „{self.object.name}“ wurde gelöscht.")
        return reverse('admin_storagelocations')


@staff_required
def admin_storagelocation_regenerate_nfc(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)
    base_choice = request.POST.get("nfc_base_choice")
    if base_choice in dict(StorageLocation.NFC_BASE_CHOICES):
        location.nfc_base_choice = base_choice
    token = uuid.uuid4().hex[:16]
    while StorageLocation.objects.filter(nfc_token=token).exists():
        token = uuid.uuid4().hex[:16]
    location.nfc_token = token
    location.save(update_fields=["nfc_token", "nfc_base_choice"])
    messages.success(request, "NFC-Token wurde neu erzeugt.")
    return redirect("admin_storagelocation_edit", pk=pk)


# ---------------------------------------------------------------------
# Overviews (Dashboards)
# ---------------------------------------------------------------------
class OverviewListView(StaffRequiredMixin, ListView):
    model = Overview
    template_name = 'inventory/admin_overviews_list.html'
    context_object_name = 'overviews'
    ordering = ["order", "name"]


@staff_required
def admin_overview_create(request):
    class _Form(forms.ModelForm):
        class Meta:
            model = Overview
            fields = [
                'name', 'slug', 'description', 'icon_emoji', 'order', 'is_active',
                'categories',
                'show_quantity', 'has_locations', 'has_min_stock',
                'enable_borrow', 'is_consumable_mode', 'require_qr',
                'enable_quick_adjust', 'show_images', 'show_tags', 'enable_mark_button',
                'enable_advanced_filters',
                'config',
            ]
            widgets = {
                'name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'slug': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'description': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
                'icon_emoji': forms.TextInput(attrs={'class': 'form-control'}),
                'order': forms.NumberInput(attrs={'class': 'form-control'}),
                'categories': forms.CheckboxSelectMultiple,
                'config': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            }
            labels = {'config': 'Erweiterte Konfiguration (JSON)'}

    if request.method == 'POST':
        form = _Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dashboard (Overview) angelegt.")
            return redirect('admin_overviews')
    else:
        form = _Form()

    return render(request, 'inventory/admin_overview_form.html', {'form': form, 'mode': 'create'})


@staff_required
def admin_overview_edit(request, pk):
    ov = get_object_or_404(Overview, pk=pk)

    class _Form(forms.ModelForm):
        class Meta:
            model = Overview
            fields = [
                'name', 'slug', 'description', 'icon_emoji', 'order', 'is_active',
                'categories',
                'show_quantity', 'has_locations', 'has_min_stock',
                'enable_borrow', 'is_consumable_mode', 'require_qr',
                'enable_quick_adjust', 'show_images', 'show_tags', 'enable_mark_button',
                'enable_advanced_filters',
                'config',
            ]
            widgets = {
                'name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'slug': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'description': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
                'icon_emoji': forms.TextInput(attrs={'class': 'form-control'}),
                'order': forms.NumberInput(attrs={'class': 'form-control'}),
                'categories': forms.CheckboxSelectMultiple,
                'config': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            }
            labels = {'config': 'Erweiterte Konfiguration (JSON)'}

    if request.method == 'POST':
        form = _Form(request.POST, instance=ov)
        if form.is_valid():
            form.save()
            messages.success(request, "Dashboard (Overview) gespeichert.")
            return redirect('admin_overviews')
    else:
        form = _Form(instance=ov)

    return render(request, 'inventory/admin_overview_form.html', {'form': form, 'mode': 'edit', 'overview': ov})


@staff_required
def admin_overview_delete(request, pk):
    ov = get_object_or_404(Overview, pk=pk)
    if request.method == 'POST':
        ov.delete()
        messages.success(request, "Dashboard (Overview) gelöscht.")
        return redirect('admin_overviews')
    return render(request, 'inventory/admin_overview_confirm_delete.html', {'overview': ov})


# ---------------------------------------------------------------------
# Feedback-Status schnell ändern
# ---------------------------------------------------------------------
@staff_required
def admin_feedback_set_status(request, pk):
    """
    Quick-Action vom Admin-Dashboard:
    POST mit 'status' = open | in_progress | done
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Nur POST erlaubt.")

    fb = get_object_or_404(Feedback, pk=pk)
    status = (request.POST.get("status") or "").strip()
    allowed = {Feedback.Status.OFFEN, Feedback.Status.IN_ARBEIT, Feedback.Status.ERLEDIGT}
    if status not in allowed:
        return HttpResponseBadRequest("Ungültiger Status.")

    fb.status = status
    fb.save(update_fields=["status", "updated_at"])
    nicename = dict(Feedback.Status.choices).get(status, status)
    messages.success(request, f"Status für „{fb.title}“ gesetzt auf: {nicename}.")
    return redirect('admin_dashboard')
