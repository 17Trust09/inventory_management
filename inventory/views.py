# inventory/views.py
import os
import uuid
from types import SimpleNamespace
from collections import defaultdict
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.views.generic import TemplateView, View, UpdateView, DeleteView, ListView
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, F, Sum, Prefetch
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model


from .forms import (
    UserRegisterForm,
    EquipmentItemForm,
    ConsumableItemForm,
    BorrowItemForm,
    FeedbackForm,
    FeedbackCommentForm,
)
from .models import (
    InventoryItem,
    Category,
    UserProfile,
    BorrowedItem,
    TagType,
    ApplicationTag,
    StorageLocation,
    Overview,
    Feedback,
    FeedbackComment,
    FeedbackVote,
)
from .integrations.homeassistant import notify_item_marked


# ---------------------------------------------------------------------------
# Hilfsfunktion: Overview + Features kontextsensitiv lesen
# ---------------------------------------------------------------------------
def _get_overview_and_features(request, default_item_type: str):
    slug = request.GET.get("o") or request.POST.get("o")
    ov = None
    features = SimpleNamespace(
        show_quantity=True,
        has_min_stock=True,
        has_locations=True,
        enable_borrow=True,
        require_qr=False,
        is_consumable_mode=(default_item_type == "consumable"),
    )
    if slug:
        try:
            ov = Overview.objects.get(slug=slug, is_active=True)
            features = ov.features()
        except Overview.DoesNotExist:
            ov = None
    return ov, features, slug


# ---------------------------------------------------------------------------
# NEU: erlaubte Overviews für einen Benutzer
# ---------------------------------------------------------------------------
def _allowed_overviews_for_user(user):
    """
    - Superuser: alle aktiven Overviews
    - sonst: nur explizit in UserProfile.allowed_overviews gesetzte aktiven Overviews
    - kein Profil / keine Auswahl -> keine Overviews
    """
    base_qs = Overview.objects.filter(is_active=True).order_by("order", "name")
    if not user.is_authenticated:
        return base_qs.none()
    if user.is_superuser:
        return base_qs

    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        return base_qs.none()
    allowed_ids = list(profile.allowed_overviews.values_list("id", flat=True))
    if not allowed_ids:
        return base_qs.none()
    return base_qs.filter(id__in=allowed_ids)


# ---------------------------------------------------------------------------
# /dashboards/ – zeigt NUR erlaubte aktive Overviews
# ---------------------------------------------------------------------------
class DashboardSelectorView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/dashboard_selector.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        allowed = _allowed_overviews_for_user(self.request.user)
        ctx["overviews"] = list(allowed)
        ctx["latest_feedback"] = list(Feedback.objects.order_by("-created_at")[:3])
        return ctx


def dashboards(request):
    """
    Kompatibilitäts-Route: gleiche Filterung wie oben.
    """
    allowed = _allowed_overviews_for_user(request.user)
    overviews = (
        allowed.prefetch_related(
            Prefetch("categories", queryset=Category.objects.only("id", "name").order_by("name"))
        )
        .order_by("order", "name")
        .distinct()
    )
    return render(request, "inventory/dashboards.html", {"overviews": overviews})


class Index(TemplateView):
    template_name = "inventory/index.html"


class TestFormView(View):
    def get(self, request):
        return render(request, "inventory/../a1_OLD/test_form.html")

    def post(self, request):
        print("✅ TESTFORMULAR WURDE ABGESCHICKT:", request.POST)
        return HttpResponse("Danke! POST erhalten.")


class SignUpView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, "inventory/signup.html", {"form": form})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save()

            # Erster User → Admin
            if User.objects.count() == 1:
                new_user.is_staff = True
                new_user.is_superuser = True
                new_user.save()

            # Optional: in Gruppe "Viewer" stecken (nur als Beispiel)
            try:
                viewer = Group.objects.get(name="Viewer")
                new_user.groups.set([viewer])
            except Group.DoesNotExist:
                pass

            user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
            )
            login(request, user)
            return redirect("index")

        return render(request, "inventory/signup.html", {"form": form})


class DashboardLanding(LoginRequiredMixin, TemplateView):
    """
    Alte Landing-Page mit Auswahl Equipment/Verbrauchsmaterial (Kompatibilität).
    """
    template_name = "inventory/../a1_OLD/dashboard_landing.html"


# ---------------------------------------------------------------------------
# Altes kombiniertes Dashboard (zeigt jetzt ALLE Items; Filter optional)
# ---------------------------------------------------------------------------
class Dashboard(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("search")
        category_filter = request.GET.get("category")
        tag_filter = request.GET.get("tag")
        location_letter = request.GET.get("location_letter")
        location_number = request.GET.get("location_number")
        item_type = request.GET.get("item_type")

        items = InventoryItem.objects.filter(overview__isnull=False).prefetch_related(
            Prefetch("borrowings", queryset=BorrowedItem.objects.filter(returned=False))
        )

        if tag_filter and tag_filter != "all":
            items = items.filter(application_tags__name=tag_filter)

        if query:
            items = items.filter(
                Q(name__icontains=query)
                | Q(location_letter__icontains=query)
                | Q(location_number__icontains=query)
            )

        if category_filter and category_filter != "all":
            items = items.filter(category__id=category_filter)

        if location_letter and location_number:
            items = items.filter(location_letter=location_letter, location_number=location_number)

        if item_type:
            items = items.filter(item_type=item_type)

        items = items.distinct().order_by("id")
        categories = Category.objects.all().order_by("name")

        borrowed_items_map = defaultdict(list)
        for item in items:
            for br in item.borrowings.all():
                borrowed_items_map[item.id].append(br)

        return render(
            request,
            "inventory/../a1_OLD/dashboard.html",
            {
                "items": items,
                "categories": categories,
                "selected_category": category_filter,
                "location_letter": location_letter,
                "location_number": location_number,
                "selected_tag": tag_filter,
                "borrowed_items_map": borrowed_items_map,
                "item_type": item_type,
            },
        )


class EquipmentDashboardView(LoginRequiredMixin, View):
    """
    Zeigt alle Equipment-Items (ohne userbasierte Tag-Whitelists).
    """
    def get(self, request, *args, **kwargs):
        items = InventoryItem.objects.filter(
            item_type="equipment",
            overview__isnull=False
        ).distinct()
        categories = Category.objects.all().order_by("name")

        selected_category = request.GET.get("category", "")
        selected_tag = request.GET.get("tag", "")

        if selected_tag and selected_tag != "all":
            items = items.filter(application_tags__name=selected_tag)
        if selected_category and selected_category != "all":
            items = items.filter(category__id=selected_category)

        return render(
            request,
            "inventory/../a1_OLD/dashboard.html",
            {
                "items": items,
                "item_type": "equipment",
                "categories": categories,
                "selected_category": selected_category,
                "selected_tag": selected_tag,
            },
        )


class ConsumableDashboardView(LoginRequiredMixin, View):
    """
    Zeigt alle Verbrauchsmaterial-Items (ohne userbasierte Tag-Whitelists).
    """
    def get(self, request, *args, **kwargs):
        items = InventoryItem.objects.filter(
            item_type="consumable",
            overview__isnull=False
        ).distinct()
        categories = Category.objects.all().order_by("name")

        selected_category = request.GET.get("category", "")
        selected_tag = request.GET.get("tag", "")

        if selected_tag and selected_tag != "all":
            items = items.filter(application_tags__name=selected_tag)
        if selected_category and selected_category != "all":
            items = items.filter(category__id=selected_category)

        return render(
            request,
            "inventory/../a1_OLD/dashboard.html",
            {
                "items": items,
                "item_type": "consumable",
                "categories": categories,
                "selected_category": selected_category,
                "selected_tag": selected_tag,
            },
        )


# ---------------------------------------------------------------------------
# Add/Edit/Delete Views (nur Login nötig)
# ---------------------------------------------------------------------------
class AddEquipmentItem(LoginRequiredMixin, View):
    def get(self, request):
        ov, features, slug = _get_overview_and_features(request, "equipment")
        form = EquipmentItemForm(user=request.user)
        return render(
            request,
            "inventory/item_form.html",
            {
                "form": form,
                "features": features,
                "overview": ov,
                "item_type": "equipment",
                "o": slug,
            },
        )

    def post(self, request):
        ov, features, slug = _get_overview_and_features(request, "equipment")
        form = EquipmentItemForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.item_type = "equipment"

            # 🔑 WICHTIG
            if ov:
                item.overview = ov

            item.save()
            form.save_m2m()
            messages.success(request, f"Artikel „{item.name}“ wurde angelegt.")
            if ov:
                return redirect("overview-dashboard", slug=ov.slug)
            return redirect("dashboards")

        return render(
            request,
            "inventory/item_form.html",
            {
                "form": form,
                "features": features,
                "overview": ov,
                "item_type": "equipment",
                "o": slug,
            },
        )



class AddConsumableItem(LoginRequiredMixin, View):
    def get(self, request):
        ov, features, slug = _get_overview_and_features(request, "consumable")
        form = ConsumableItemForm(user=request.user)
        return render(
            request,
            "inventory/item_form.html",
            {
                "form": form,
                "features": features,
                "overview": ov,
                "item_type": "consumable",
                "o": slug,
            },
        )

    def post(self, request):
        ov, features, slug = _get_overview_and_features(request, "consumable")
        form = ConsumableItemForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.item_type = "consumable"

            # 🔑 WICHTIG
            if ov:
                item.overview = ov

            item.save()
            form.save_m2m()
            messages.success(request, f"Artikel „{item.name}“ wurde angelegt.")
            if ov:
                return redirect("overview-dashboard", slug=ov.slug)
            return redirect("dashboards")

        return render(
            request,
            "inventory/item_form.html",
            {
                "form": form,
                "features": features,
                "overview": ov,
                "item_type": "consumable",
                "o": slug,
            },
        )



class EditItem(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    template_name = "inventory/item_form.html"

    def get_form_class(self):
        item = self.get_object()
        return ConsumableItemForm if item.item_type == "consumable" else EquipmentItemForm

    def get_success_url(self):
        nxt = self.request.POST.get("next") or self.request.GET.get("next")
        if nxt:
            return nxt

        item = self.get_object()
        if item.overview:
            return reverse_lazy(
                "overview-dashboard",
                kwargs={"slug": item.overview.slug}
            )

        return reverse_lazy("dashboards")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields["category"].queryset = Category.objects.all().order_by("name")
        tag_qs = (
            ApplicationTag.objects
            .exclude(name="-")
            .exclude(name__startswith="__ov::")
            .order_by("name")
        )
        form.fields["application_tags"].queryset = tag_qs
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        item = self.get_object()

        ov, features, slug = _get_overview_and_features(
            self.request,
            default_item_type=item.item_type or "equipment"
        )

        # 🔑 Dashboard-Auswahl für "Item verschieben"
        if self.request.user.is_superuser:
            overview_list = Overview.objects.filter(is_active=True)
        else:
            profile = UserProfile.objects.filter(user=self.request.user).first()
            overview_list = (
                profile.allowed_overviews.filter(is_active=True)
                if profile else Overview.objects.none()
            )

        ctx.update(
            {
                "features": features,
                "overview": ov,
                "o": slug,
                "next": self.request.GET.get("next", ""),
                "item_type": item.item_type or "equipment",
                "similar_items": [],
                "overview_list": overview_list,  # 👈 WICHTIG
                "nfc_url": self.request.build_absolute_uri(
                    reverse("nfc-redirect", kwargs={"token": item.nfc_token})
                )
                if item.nfc_token
                else "",
            }
        )
        return ctx


class MoveItemToOverviewView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)

        # 🔒 Item-Besitz prüfen
        if not request.user.is_superuser and item.user != request.user:
            messages.error(request, "Du darfst dieses Item nicht verschieben.")
            return redirect("edit-item", pk=pk)

        target_id = request.POST.get("target_overview")
        if not target_id:
            messages.error(request, "Kein Ziel-Dashboard angegeben.")
            return redirect("edit-item", pk=pk)

        target = get_object_or_404(Overview, pk=target_id, is_active=True)

        # 🔒 Ziel-Dashboard-Rechte prüfen
        if not request.user.is_superuser:
            profile = UserProfile.objects.filter(user=request.user).first()
            if not profile or not profile.allowed_overviews.filter(pk=target.pk).exists():
                messages.error(request, "Du darfst dieses Dashboard nicht verwenden.")
                return redirect("edit-item", pk=pk)

        old = item.overview
        item.overview = target
        item.save(update_fields=["overview"])

        messages.success(
            request,
            f"Artikel wurde von „{old.name if old else '-'}“ nach „{target.name}“ verschoben."
        )

        return redirect("overview-dashboard", slug=target.slug)


# ---------------------------------------------------------------------------
# Verleihen / Rückgabe
# ---------------------------------------------------------------------------
class BorrowedItemsView(LoginRequiredMixin, View):
    def _safe_redirect(self, request, url: str):
        if url and url_has_allowed_host_and_scheme(
            url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(url)
        try:
            return redirect("dashboards")
        except Exception:
            return redirect("dashboard-equipment")

    def get(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id)
        form = BorrowItemForm(item=item)
        next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or ""
        return render(
            request,
            "inventory/borrow_item.html",
            {
                "item": item,
                "form": form,
                "next": next_url,
            },
        )

    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id)
        form = BorrowItemForm(request.POST, item=item)
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or ""

        if form.is_valid():
            borrowed = form.save(commit=False)
            borrowed.item = item
            borrowed.save()
            item.quantity -= borrowed.quantity_borrowed
            item.save()
            messages.success(request, f"{borrowed.quantity_borrowed}x {item.name} an {borrowed.borrower} verliehen.")
            return self._safe_redirect(request, next_url)

        return render(
            request,
            "inventory/borrow_item.html",
            {
                "item": item,
                "form": form,
                "next": next_url,
            },
        )


class ReturnItemView(LoginRequiredMixin, View):
    def post(self, request, borrow_id):
        borrowed = get_object_or_404(BorrowedItem, id=borrow_id)
        if not borrowed.returned:
            borrowed.return_item()
            messages.success(request, f"{borrowed.quantity_borrowed}x {borrowed.item.name} zurückgegeben.")
        else:
            messages.info(request, "Dieser Artikel wurde bereits zurückgegeben.")
        nxt = self.request.POST.get("next") or self.request.GET.get("next")
        if nxt:
            return redirect(nxt)
        return redirect(
            "dashboard-equipment" if borrowed.item.item_type == "equipment" else "dashboard-consumables"
        )


# ---------------------------------------------------------------------------
# Bild/QR/Barcode & Delete
# ---------------------------------------------------------------------------
class RegenerateQRView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        if not request.user.is_superuser and item.user != request.user:
            messages.error(request, "Du darfst dieses Item nicht verschieben.")
            return redirect("edit-item", pk=pk)
        item.generate_qr_code()
        messages.success(request, "QR-Code wurde neu generiert.")
        o = request.POST.get("o") or request.GET.get("o") or ""
        nxt = request.POST.get("next") or request.GET.get("next") or ""
        url = reverse("edit-item", kwargs={"pk": pk})
        q = []
        if o:
            q.append(f"o={o}")
        if nxt:
            from urllib.parse import quote

            q.append(f"next={quote(nxt)}")
        if q:
            url = f"{url}?{'&'.join(q)}"
        return redirect(url)


class RegenerateNFCTokenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        if not request.user.is_superuser and item.user != request.user:
            messages.error(request, "Du darfst dieses Item nicht bearbeiten.")
            return redirect("edit-item", pk=pk)

        token = uuid.uuid4().hex[:16]
        while InventoryItem.objects.filter(nfc_token=token).exists():
            token = uuid.uuid4().hex[:16]
        item.nfc_token = token
        item.save(update_fields=["nfc_token"])
        messages.success(request, "NFC-Token wurde neu erzeugt.")

        o = request.POST.get("o") or request.GET.get("o") or ""
        nxt = request.POST.get("next") or request.GET.get("next") or ""
        url = reverse("edit-item", kwargs={"pk": pk})
        q = []
        if o:
            q.append(f"o={o}")
        if nxt:
            from urllib.parse import quote

            q.append(f"next={quote(nxt)}")
        if q:
            url = f"{url}?{'&'.join(q)}"
        return redirect(url)


class DeleteImageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        if item.image:
            path = item.image.path
            item.image.delete()
            if os.path.exists(path):
                os.remove(path)
            messages.success(request, "Bild wurde gelöscht.")
        else:
            messages.info(request, "Kein Bild vorhanden.")
        o = request.POST.get("o") or request.GET.get("o") or ""
        nxt = request.POST.get("next") or request.GET.get("next") or ""
        url = reverse("edit-item", kwargs={"pk": pk})
        q = []
        if o:
            q.append(f"o={o}")
        if nxt:
            from urllib.parse import quote

            q.append(f"next={quote(nxt)}")
        if q:
            url = f"{url}?{'&'.join(q)}"
        return redirect(url)


class DeleteItem(LoginRequiredMixin, DeleteView):
    model = InventoryItem

    def get_template_names(self):
        return ["inventory/delete_item.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self.request.GET.get("next", "")
        return ctx

    def get_success_url(self):
        nxt = self.request.POST.get("next") or self.request.GET.get("next")
        if nxt:
            return nxt
        try:
            return reverse_lazy("admin_items")
        except Exception:
            pass
        itype = self.request.POST.get("item_type") or self.request.GET.get("item_type")
        if itype == "equipment":
            return reverse_lazy("dashboard-equipment")
        if itype == "consumable":
            return reverse_lazy("dashboard-consumables")
        return reverse_lazy("dashboard")


class ScanBarcodeView(LoginRequiredMixin, View):
    def get(self, request):
        barcode = request.GET.get("barcode")
        if barcode:
            item = get_object_or_404(InventoryItem, barcode=barcode)
            o = request.GET.get("o", "")
            nxt = request.GET.get("next", "")
            url = reverse("edit-item", kwargs={"pk": item.id})
            q = []
            if o:
                q.append(f"o={o}")
            if nxt:
                from urllib.parse import quote

                q.append(f"next={quote(nxt)}")
            if q:
                url = f"{url}?{'&'.join(q)}"
            return redirect(url)
        messages.error(request, "Kein Barcode übergeben.")
        return redirect("dashboard")


class BarcodeListView(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.all().order_by("id")
        return render(request, "inventory/barcode_list.html", {"items": items})


# ---------------------------------------------------------------------------
# Home Assistant Demo-API (nur Login nötig)
# ---------------------------------------------------------------------------
class MarkItemAPI(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id)
        ok = notify_item_marked(item, user=request.user)
        if ok:
            messages.success(request, f"{item.name} wurde an Home Assistant gemeldet.")
        else:
            messages.error(request, "Home Assistant konnte nicht erreicht werden.")

        next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("dashboards")


class NFCItemRedirectView(LoginRequiredMixin, View):
    def get(self, request, token):
        item = get_object_or_404(InventoryItem, nfc_token=token)
        url = reverse("edit-item", kwargs={"pk": item.id})
        o = request.GET.get("o", "")
        nxt = request.GET.get("next", "")
        q = []
        if o:
            q.append(f"o={o}")
        if nxt:
            from urllib.parse import quote

            q.append(f"next={quote(nxt)}")
        if q:
            url = f"{url}?{'&'.join(q)}"
        return redirect(url)


class NFCStorageLocationView(LoginRequiredMixin, View):
    def get(self, request, token):
        location = get_object_or_404(StorageLocation, nfc_token=token)
        items = InventoryItem.objects.filter(
            storage_location=location,
            is_active=True,
        ).select_related("overview", "category")

        if not request.user.is_superuser:
            allowed_overviews = _allowed_overviews_for_user(request.user)
            items = items.filter(overview__in=allowed_overviews)

        items = items.order_by("name")

        return render(
            request,
            "inventory/storage_location_items.html",
            {
                "location": location,
                "items": items,
            },
        )


class DrawerItemsAPI(LoginRequiredMixin, View):
    def get(self, request, location_letter, location_number):
        items = InventoryItem.objects.filter(
            location_letter=location_letter, location_number=location_number, is_active=True
        )
        data = [{"id": it.id, "name": it.name, "quantity": it.quantity} for it in items]
        return JsonResponse(data, safe=False)


class QRCodeListAdminView(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.all().order_by("id")
        return render(request, "inventory/admin_qr_code_list.html", {"items": items})


# ---------------------------------------------------------------------------
# Neues, modulares Overview-Dashboard (mit Whitelist-Check je User)
# ---------------------------------------------------------------------------
class OverviewDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/overview_dashboard.html"

    SORT_MAP = {
        "name": "name",
        "category": "category__name",
        "location": "storage_location__name",
        "quantity": "quantity",
        "min": "low_quantity",
        "borrowed": "borrowed_open",
    }
    DEFAULT_SORT = "name"

    def dispatch(self, request, *args, **kwargs):
        self.overview = get_object_or_404(Overview, slug=kwargs["slug"], is_active=True)

        if not request.user.is_superuser:
            profile = UserProfile.objects.filter(user=request.user).first()
            allowed = profile.allowed_overviews.filter(pk=self.overview.pk).exists() if profile else False
            if not allowed:
                messages.error(request, "Du hast keinen Zugriff auf dieses Dashboard.")
                return redirect("dashboards")

        return super().dispatch(request, *args, **kwargs)

    def base_queryset(self):
        open_borrowings = Prefetch(
            "borrowings",
            queryset=BorrowedItem.objects.filter(returned=False),
            to_attr="prefetched_open_borrowings",
        )

        qs = (
            InventoryItem.objects
            .filter(overview=self.overview)  # 🔑 HIER ist der Fix
            .select_related("category", "storage_location", "user")
            .prefetch_related("application_tags", open_borrowings)
            .annotate(
                borrowed_open=Sum(
                    "borrowings__quantity_borrowed",
                    filter=Q(borrowings__returned=False)
                )
            )
        )
        return qs


    def apply_filters(self, qs):
        request = self.request
        q = request.GET.get("q", "").strip()
        category_id = request.GET.get("category", "").strip()
        tag_name = request.GET.get("tag", "").strip()
        storage_location_id = request.GET.get("storage_location", "").strip()
        loc_letter = request.GET.get("location_letter", "").strip()
        loc_number = request.GET.get("location_number", "").strip()
        only_low = request.GET.get("only_low", "") == "1"

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(barcode__icontains=q)
                | Q(location_letter__icontains=q)
                | Q(location_number__icontains=q)
            )

        if category_id and category_id != "all":
            qs = qs.filter(category_id=category_id)

        if tag_name and tag_name != "all":
            qs = qs.filter(application_tags__name=tag_name)

        if storage_location_id:
            qs = qs.filter(storage_location_id=storage_location_id)

        if loc_letter:
            qs = qs.filter(location_letter__iexact=loc_letter)
        if loc_number:
            qs = qs.filter(location_number__iexact=loc_number)

        if only_low and self.overview.has_min_stock:
            qs = qs.filter(quantity__lt=F("low_quantity"))

        return qs.distinct()

    def apply_sort(self, qs):
        sort_key = self.request.GET.get("sort", self.DEFAULT_SORT)
        order = self.request.GET.get("order", "asc")
        field = self.SORT_MAP.get(sort_key, self.SORT_MAP[self.DEFAULT_SORT])
        if order == "desc":
            field = f"-{field}"
        return qs.order_by(field), sort_key, order

    def get_auxiliary_choices(self):
        cats = list(self.overview.categories.all())
        if not cats:
            cats = list(Category.objects.all().order_by("name"))

        try:
            tagtype_name = "Verbrauchsmaterial" if self.overview.is_consumable_mode else "Equipment"
            tt = TagType.objects.get(name=tagtype_name)
            tags = list(ApplicationTag.objects.filter(type=tt).order_by("name"))
        except TagType.DoesNotExist:
            tags = list(ApplicationTag.objects.all().order_by("name"))

        return cats, tags

    def _compute_add_url(self):
        if self.overview.is_consumable_mode:
            try:
                return reverse("add-consumable")
            except NoReverseMatch:
                try:
                    return reverse("add-verbrauch")
                except NoReverseMatch:
                    return "/add-verbrauch/"
        else:
            try:
                return reverse("add-equipment")
            except NoReverseMatch:
                return "/add-equipment/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.base_queryset()
        qs = self.apply_filters(qs)
        qs, sort_key, order = self.apply_sort(qs)

        try:
            per_page = int(self.request.GET.get("page_size", "25"))
        except ValueError:
            per_page = 25
        per_page = max(5, min(per_page, 200))
        paginator = Paginator(qs, per_page)
        page_number = self.request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)

        def next_order_for(col):
            if sort_key == col and order == "asc":
                return "desc"
            return "asc"

        cats, tags = self.get_auxiliary_choices()
        storage_locations = list(
            StorageLocation.objects.filter(items__overview=self.overview)
            .distinct()
        )
        storage_locations.sort(key=lambda loc: loc.get_full_path().lower())

        ctx.update(
            {
                "overview": self.overview,
                "features": self.overview.features(),
                "items": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
                "per_page": per_page,
                "q": self.request.GET.get("q", "").strip(),
                "selected_category": self.request.GET.get("category", ""),
                "selected_tag": self.request.GET.get("tag", ""),
                "selected_storage_location": self.request.GET.get("storage_location", ""),
                "location_letter": self.request.GET.get("location_letter", ""),
                "location_number": self.request.GET.get("location_number", ""),
                "only_low": self.request.GET.get("only_low", "") == "1",
                "sort_key": sort_key,
                "order": order,
                "next_order": {
                    "name": next_order_for("name"),
                    "category": next_order_for("category"),
                    "location": next_order_for("location"),
                    "quantity": next_order_for("quantity"),
                    "min": next_order_for("min"),
                    "borrowed": next_order_for("borrowed"),
                },
                "categories": cats,
                "tags": tags,
                "storage_locations": storage_locations,
                "add_url": self._compute_add_url(),
            }
        )
        return ctx


# ============================================================================
# Feedback – Liste, Detail, Erstellen, Votes, Kommentare (nur Login nötig)
# ============================================================================
class FeedbackListView(LoginRequiredMixin, ListView):
    model = Feedback
    template_name = "inventory/feedback_list.html"
    context_object_name = "feedback_list"
    paginate_by = 20

    def get_queryset(self):
        qs = Feedback.objects.select_related("created_by", "assignee").order_by("-created_at")
        status_param = (self.request.GET.get("status") or "").strip().lower()

        # deutsche & englische Aliase erlauben
        aliases = {
            "offen": Feedback.Status.OFFEN,
            "open": Feedback.Status.OFFEN,

            "in_progress": Feedback.Status.IN_ARBEIT,
            "in arbeit": Feedback.Status.IN_ARBEIT,
            "in-arbeits": Feedback.Status.IN_ARBEIT,  # tolerant
            "in-progress": Feedback.Status.IN_ARBEIT,

            "done": Feedback.Status.ERLEDIGT,
            "erledigt": Feedback.Status.ERLEDIGT,
            "closed": Feedback.Status.ERLEDIGT,
            "geschlossen": Feedback.Status.ERLEDIGT,
        }

        if status_param in aliases:
            qs = qs.filter(status=aliases[status_param])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


class FeedbackDetailView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/feedback_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fb = get_object_or_404(
            Feedback.objects.select_related("created_by", "assignee"),
            pk=kwargs.get("pk"),
        )
        comments = fb.comments.select_related("author").order_by("created_at")

        existing_vote = None
        if self.request.user.is_authenticated:
            existing_vote = FeedbackVote.objects.filter(feedback=fb, user=self.request.user).first()

        ctx.update(
            {
                "feedback": fb,
                "comments": comments,
                "comment_form": FeedbackCommentForm(),
                "user_vote": existing_vote.value if existing_vote else 0,
            }
        )
        return ctx


class FeedbackCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = FeedbackForm()
        return render(request, "inventory/feedback_form.html", {"form": form})

    def post(self, request):
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.created_by = request.user
            fb.save()
            messages.success(request, "Feedback wurde erstellt.")
            return redirect("feedback-list")
        return render(request, "inventory/feedback_form.html", {"form": form})


class FeedbackVoteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fb = get_object_or_404(Feedback, pk=pk)
        v = (request.GET.get("v") or request.POST.get("v") or "").strip().lower()
        value = 1 if v == "up" else -1 if v == "down" else None
        if value is None:
            messages.error(request, "Ungültige Abstimmung.")
            return redirect("feedback-detail", pk=pk)

        vote, created = FeedbackVote.objects.get_or_create(
            feedback=fb, user=request.user, defaults={"value": value}
        )
        if not created:
            if vote.value == value:
                vote.delete()
                messages.info(request, "Deine Stimme wurde entfernt.")
            else:
                vote.value = value
                vote.save(update_fields=["value"])
                messages.success(request, "Deine Stimme wurde aktualisiert.")
        else:
            messages.success(request, "Deine Stimme wurde gezählt.")

        return redirect("feedback-detail", pk=pk)


class FeedbackCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fb = get_object_or_404(Feedback, pk=pk)
        form = FeedbackCommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.feedback = fb
            c.author = request.user
            c.save()
            messages.success(request, "Kommentar hinzugefügt.")
        else:
            messages.error(request, "Kommentar konnte nicht gespeichert werden.")
        return redirect("feedback-detail", pk=pk)

# --------------------------------------------------------
# Login: Benutzer ist deaktiviert -> klare Fehlermeldung
# --------------------------------------------------------
class CustomAuthForm(AuthenticationForm):
    """
    Zeigt eine klare Meldung, wenn das Konto deaktiviert ist.
    Wir überschreiben NUR confirm_login_allowed – so kommt die Meldung genau einmal.
    """
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Benutzername oder Passwort ist falsch. "
            "Bitte Groß-/Kleinschreibung beachten."
        ),
        "inactive": "❌ Dieses Konto ist deaktiviert. Bitte wenden Sie sich an den Administrator.",
    }

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(self.error_messages["inactive"], code="inactive")

    def clean(self):
        # Feldwerte direkt aus dem POST
        username = (self.data.get("username") or "").strip()
        password = (self.data.get("password") or "")

        if username and password:
            UserModel = get_user_model()
            try:
                user = UserModel._default_manager.get(**{UserModel.USERNAME_FIELD: username})
            except UserModel.DoesNotExist:
                user = None

            # Passwort korrekt + User inaktiv -> eigene, klare Meldung
            if user is not None and not user.is_active and user.check_password(password):
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")

        # Standard-Validierung (liefert ggf. 'invalid_login')
        return super().clean()
