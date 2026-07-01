"""
Item-CRUD-Views: Add, Edit, Delete, RegenerateQR/NFC, History-Rollback, Move, BulkActions.
"""
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import UpdateView, DeleteView, View
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum, Prefetch
from django.utils import timezone

from ..forms import (
    EquipmentItemForm,
    ConsumableItemForm,
)
from ..models import (
    InventoryItem,
    InventoryHistory,
    Category,
    UserProfile,
    Overview,
)
from .helpers import (
    _get_overview_and_features,
    safe_redirect_or,
    extract_next,
    _snapshot_item,
    _build_changes,
    _create_history_entry,
    MOVEMENT_FIELDS,
)


# ---------------------------------------------------------------------------
# Add Equipment
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
                "tag_type_name": "Equipment",
            },
        )

    def post(self, request):
        ov, features, slug = _get_overview_and_features(request, "equipment")
        form = EquipmentItemForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.item_type = "equipment"
            if ov:
                item.overview = ov
            item.save()
            form.save_m2m()
            _create_history_entry(
                item=item,
                user=request.user,
                action=InventoryHistory.Action.CREATED,
                after=_snapshot_item(item),
                meta={"source": "create"},
            )
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
                "tag_type_name": "Equipment",
            },
        )


# ---------------------------------------------------------------------------
# Add Consumable
# ---------------------------------------------------------------------------
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
                "tag_type_name": "Verbrauchsmaterial",
            },
        )

    def post(self, request):
        ov, features, slug = _get_overview_and_features(request, "consumable")
        form = ConsumableItemForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.item_type = "consumable"
            if ov:
                item.overview = ov
            item.save()
            form.save_m2m()
            _create_history_entry(
                item=item,
                user=request.user,
                action=InventoryHistory.Action.CREATED,
                after=_snapshot_item(item),
                meta={"source": "create"},
            )
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
                "tag_type_name": "Verbrauchsmaterial",
            },
        )


# ---------------------------------------------------------------------------
# Edit Item
# ---------------------------------------------------------------------------
class EditItem(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    template_name = "inventory/item_form.html"

    def get_form_class(self):
        item = self.get_object()
        return ConsumableItemForm if item.item_type == "consumable" else EquipmentItemForm

    def get_success_url(self):
        nxt = extract_next(self.request)
        item = self.get_object()
        if item.overview:
            return safe_redirect_or(self.request, nxt,
                fallback_view="overview-dashboard",
                fallback_kwargs={"slug": item.overview.slug})
        return safe_redirect_or(self.request, nxt, fallback_view="dashboards")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        from ..models import ApplicationTag
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
        from ..models import User as AuthUser
        history_entries = InventoryHistory.objects.filter(item=item).select_related("user")
        history_action = (self.request.GET.get("history_action") or "").strip()
        history_user = (self.request.GET.get("history_user") or "").strip()
        history_days = (self.request.GET.get("history_days") or "").strip()
        if history_action:
            history_entries = history_entries.filter(action=history_action)
        if history_user:
            history_entries = history_entries.filter(user_id=history_user)
        if history_days:
            try:
                days = int(history_days)
                since = timezone.now() - timedelta(days=days)
                history_entries = history_entries.filter(created_at__gte=since)
            except ValueError:
                history_days = ""
        history_entries = history_entries.order_by("-created_at")[:50]
        history_users = (
            AuthUser.objects.filter(inventory_history_entries__item=item)
            .distinct()
            .order_by("username")
        )

        ov, features, slug = _get_overview_and_features(
            self.request,
            default_item_type=item.item_type or "equipment"
        )

        if self.request.user.is_superuser:
            overview_list = Overview.objects.filter(is_active=True)
        else:
            profile = UserProfile.objects.filter(user=self.request.user).first()
            overview_list = (
                profile.allowed_overviews.filter(is_active=True)
                if profile else Overview.objects.none()
            )

        from ..helpers import _resolve_nfc_base_url

        ctx.update({
            "features": features,
            "overview": ov,
            "o": slug,
            "next": self.request.GET.get("next", ""),
            "item_type": item.item_type or "equipment",
            "similar_items": [],
            "overview_list": overview_list,
            "nfc_url": (
                f"{_resolve_nfc_base_url(self.request, item.nfc_base_choice)}"
                f"{reverse('nfc-redirect', kwargs={'token': item.nfc_token})}"
            ) if item.nfc_token else "",
            "history_entries": history_entries,
            "history_action": history_action,
            "history_user": history_user,
            "history_days": history_days,
            "history_action_choices": InventoryHistory.Action.choices,
            "history_users": history_users,
            "attachments": item.attachments.all(),
            "tag_type_name": "Equipment" if item.item_type == "equipment" else "Verbrauchsmaterial",
            "breadcrumbs": [{"name": "Dashboards", "url": reverse("dashboards")}],
        })
        if item.overview:
            ctx["breadcrumbs"].append({
                "name": f"{item.overview.icon_emoji} {item.overview.name}",
                "url": reverse("overview-dashboard", kwargs={"slug": item.overview.slug}),
            })
        ctx["breadcrumbs"].append({"name": item.name, "url": None})
        return ctx

    def form_valid(self, form):
        item = self.get_object()
        before = _snapshot_item(item)
        response = super().form_valid(form)
        item.refresh_from_db()
        after = _snapshot_item(item)
        changes = _build_changes(before, after)
        if not changes:
            return response
        movement_changes = [c for c in changes if c["field"] in MOVEMENT_FIELDS]
        other_changes = [c for c in changes if c["field"] not in MOVEMENT_FIELDS]
        if movement_changes:
            _create_history_entry(
                item=item, user=self.request.user,
                action=InventoryHistory.Action.MOVEMENT,
                before=before, after=after,
                changes=movement_changes, meta={"source": "edit"},
            )
        if other_changes:
            _create_history_entry(
                item=item, user=self.request.user,
                action=InventoryHistory.Action.EDITED,
                before=before, after=after,
                changes=other_changes, meta={"source": "edit"},
            )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Bitte korrigiere die markierten Fehler.")
        return self.render_to_response(self.get_context_data(form=form))


# ---------------------------------------------------------------------------
# Delete Item
# ---------------------------------------------------------------------------
class DeleteItem(LoginRequiredMixin, DeleteView):
    model = InventoryItem
    template_name = "inventory/delete_item.html"

    def get_success_url(self):
        item = self.get_object()
        nxt = extract_next(self.request)
        if item.overview:
            return safe_redirect_or(self.request, nxt,
                fallback_view="overview-dashboard",
                fallback_kwargs={"slug": item.overview.slug})
        return safe_redirect_or(self.request, nxt, fallback_view="dashboards")

    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        _create_history_entry(
            item=item, user=request.user,
            action=InventoryHistory.Action.DELETED,
            before=_snapshot_item(item),
            meta={"source": "delete"},
        )
        name = item.name
        url = self.get_success_url()
        item.delete()
        messages.success(request, f"Artikel „{name}“ wurde gelöscht.")
        return redirect(url)


# ---------------------------------------------------------------------------
# History Rollback
# ---------------------------------------------------------------------------
class ItemHistoryRollbackView(LoginRequiredMixin, View):
    def post(self, request, pk, history_id):
        item = get_object_or_404(InventoryItem, pk=pk)
        history_entry = get_object_or_404(InventoryHistory, pk=history_id, item=item)
        if not history_entry.data_after:
            messages.error(request, "Dieser Historie-Eintrag enthält keine Wiederherstellungsdaten.")
            nxt = extract_next(request)
            return safe_redirect_or(request, nxt, fallback_view="edit-item", fallback_kwargs={"pk": pk})
        before = _snapshot_item(item)
        after = history_entry.data_after
        for field, value in after.items():
            if field == "tags":
                from ..models import ApplicationTag
                if before.get("tags"):
                    item.application_tags.set(value)
                elif value:
                    item.application_tags.set(value)
                else:
                    item.application_tags.clear()
                continue
            if field == "maintenance_date":
                from datetime import date
                from ..models import ApplicationTag
                item.maintenance_date = date.fromisoformat(value) if value else None
                continue
            if hasattr(item, field) and field not in ("id",):
                setattr(item, field, value)
        item.save()
        _create_history_entry(
            item=item, user=request.user,
            action=InventoryHistory.Action.ROLLBACK,
            before=before, after=_snapshot_item(item),
            meta={"source": "rollback", "rolled_back_from": history_id},
        )
        messages.success(request, f"Artikel „{item.name}“ wurde auf den Stand vom "
                                   f"{history_entry.created_at.strftime('%d.%m.%Y %H:%M')} zurückgesetzt.")
        return redirect("edit-item", pk=pk)


# ---------------------------------------------------------------------------
# Move to Overview
# ---------------------------------------------------------------------------
class MoveItemToOverviewView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        target_id = request.POST.get("overview_id")
        if not target_id:
            messages.error(request, "Bitte wähle ein Dashboard aus.")
            return redirect("edit-item", pk=pk)
        target = get_object_or_404(Overview, pk=target_id, is_active=True)
        before = _snapshot_item(item)
        item.overview = target
        item.save(update_fields=["overview"])
        after = _snapshot_item(item)
        _create_history_entry(
            item=item, user=request.user,
            action=InventoryHistory.Action.MOVEMENT,
            before=before, after=after,
            meta={"source": "move-item"},
        )
        messages.success(request, f"„{item.name}“ wurde nach „{target.icon_emoji} {target.name}“ verschoben.")
        return redirect("overview-dashboard", slug=target.slug)


# ---------------------------------------------------------------------------
# Regenerate QR
# ---------------------------------------------------------------------------
class RegenerateQRView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from ..models import InventoryItem
        item = get_object_or_404(InventoryItem, pk=pk)
        qr_code = item.generate_qr_code(regenerate=True)
        if qr_code:
            messages.success(request, f"QR-Code für „{item.name}“ neu generiert.")
        else:
            messages.warning(request, f"QR-Code-Generierung für „{item.name}“ fehlgeschlagen.")
        return redirect("edit-item", pk=pk)


# ---------------------------------------------------------------------------
# Regenerate NFC
# ---------------------------------------------------------------------------
class RegenerateNFCTokenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        import uuid
        item = get_object_or_404(InventoryItem, pk=pk)
        item.nfc_token = str(uuid.uuid4())
        item.save(update_fields=["nfc_token"])
        messages.success(request, f"NFC-Token für „{item.name}“ neu generiert.")
        return redirect("edit-item", pk=pk)


# ---------------------------------------------------------------------------
# Delete Image
# ---------------------------------------------------------------------------
class DeleteImageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        if item.image:
            item.image.delete(save=False)
            item.image = None
            item.save(update_fields=["image"])
            messages.success(request, "Bild gelöscht.")
        return redirect("edit-item", pk=pk)


# ---------------------------------------------------------------------------
# Bulk Actions
# ---------------------------------------------------------------------------
class BulkItemActionView(LoginRequiredMixin, View):
    def post(self, request):
        item_ids = request.POST.getlist("selected_items")
        action = request.POST.get("bulk_action")
        overview_id = request.POST.get("overview_id")

        if not item_ids or not action:
            messages.warning(request, "Keine Aktion oder keine Items ausgewählt.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        items = InventoryItem.objects.filter(id__in=item_ids, overview__isnull=False)

        if action == "move" and overview_id:
            target = get_object_or_404(Overview, pk=overview_id, is_active=True)
            count = 0
            for item in items:
                before = _snapshot_item(item)
                item.overview = target
                item.save(update_fields=["overview"])
                after = _snapshot_item(item)
                _create_history_entry(
                    item=item, user=request.user,
                    action=InventoryHistory.Action.MOVEMENT,
                    before=before, after=after,
                    meta={"source": "bulk-move"},
                )
                count += 1
            messages.success(request, f"{count} Item(s) nach „{target.name}“ verschoben.")

        elif action == "delete":
            count = 0
            for item in items:
                _create_history_entry(
                    item=item, user=request.user,
                    action=InventoryHistory.Action.DELETED,
                    before=_snapshot_item(item),
                    meta={"source": "bulk-delete"},
                )
                item.delete()
                count += 1
            messages.success(request, f"{count} Item(s) gelöscht.")

        elif action == "favorite":
            count = 0
            for item in items:
                item.is_favorite = True
                item.save(update_fields=["is_favorite"])
                count += 1
            messages.success(request, f"{count} Item(s) als Favorit markiert.")

        else:
            messages.warning(request, "Unbekannte Aktion.")

        return redirect(request.META.get("HTTP_REFERER", "/"))


__all__ = [
    "AddEquipmentItem", "AddConsumableItem", "EditItem", "DeleteItem",
    "DeleteImageView", "RegenerateQRView", "RegenerateNFCTokenView",
    "ItemHistoryRollbackView", "MoveItemToOverviewView", "BulkItemActionView",
]
