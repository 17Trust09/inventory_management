"""
API-ähnliche Item-Views: Mark, QuickAdjust, NFC-Redirects, Attachments, Comments.
"""
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import View
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum, Prefetch
from django.utils import timezone

from ..forms import ItemCommentForm
from ..models import (
    InventoryItem,
    InventoryHistory,
    ItemAttachment,
    ItemComment,
    UserProfile,
    BorrowedItem,
    TagType,
    ApplicationTag,
    StorageLocation,
    GlobalSettings,
    Overview,
    ItemMark,
)
from ..integrations.homeassistant import notify_item_marked
from .helpers import (
    safe_redirect_or,
    extract_next,
    _resolve_nfc_base_url,
    _snapshot_item,
    _create_history_entry,
)


# ---------------------------------------------------------------------------
# Mark Items (ESP32 / Barcode-Marker)
# ---------------------------------------------------------------------------
class MarkItemAPI(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        action = request.POST.get("action", "mark")
        now = timezone.now()

        gs = GlobalSettings.objects.first()
        auto_clear = getattr(gs, "esp_mark_auto_clear_seconds", None)

        if action == "mark":
            mark, created = ItemMark.objects.get_or_create(
                item=item,
                defaults={"marked_by": request.user, "marked_at": now},
            )
            if not created:
                mark.marked_by = request.user
                mark.marked_at = now
                mark.save()
            try:
                notify_item_marked(item, request.user)
            except Exception:
                pass
            return JsonResponse({
                "status": "marked",
                "item": item.name,
                "auto_clear_seconds": auto_clear,
            })
        elif action == "unmark":
            ItemMark.objects.filter(item=item).delete()
            return JsonResponse({"status": "unmarked", "item": item.name})
        return JsonResponse({"error": "Unbekannte Aktion"}, status=400)


# ---------------------------------------------------------------------------
# Quick Adjust Quantity
# ---------------------------------------------------------------------------
class QuickAdjustQuantityView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        try:
            change = int(request.POST.get("change", "0"))
        except ValueError:
            messages.error(request, "Ungültiger Wert.")
            return redirect(request.META.get("HTTP_REFERER", "dashboards"))
        if change == 0:
            messages.info(request, "Keine Änderung.")
            return redirect(request.META.get("HTTP_REFERER", "dashboards"))

        before = _snapshot_item(item)
        item.quantity = max(0, item.quantity + change)
        item.save(update_fields=["quantity"])
        after = _snapshot_item(item)
        _create_history_entry(
            item=item, user=request.user,
            action=InventoryHistory.Action.ADJUSTED,
            before=before, after=after,
            meta={"source": "quick-adjust", "delta": change},
        )
        direction = "erhöht" if change > 0 else "reduziert"
        messages.success(request, f"Bestand von „{item.name}“ um {abs(change)} {direction}.")
        return redirect(request.META.get("HTTP_REFERER", "dashboards"))


# ---------------------------------------------------------------------------
# NFC Redirects
# ---------------------------------------------------------------------------
class NFCItemRedirectView(LoginRequiredMixin, View):
    def get(self, request, token):
        item = get_object_or_404(InventoryItem, nfc_token=token)
        return render(request, "inventory/item_nfc.html", {"item": item, "nfc_token": token})


class NFCStorageLocationView(LoginRequiredMixin, View):
    def get(self, request, token):
        loc = get_object_or_404(StorageLocation, nfc_token=token)
        items = loc.items.filter(is_active=True, quantity__gt=0).order_by("name")[:20]
        return render(request, "inventory/location_nfc.html", {"location": loc, "items": items})


# ---------------------------------------------------------------------------
# Drawer / QR Code Admin
# ---------------------------------------------------------------------------
class DrawerItemsAPI(LoginRequiredMixin, View):
    def get(self, request):
        letter = request.GET.get("letter", "").strip().upper()
        number = request.GET.get("number", "").strip()
        bucket = request.GET.get("bucket")
        if not letter and not number and not bucket:
            return HttpResponseBadRequest("Bitte letter, number oder bucket angeben.")
        if letter and number:
            items = InventoryItem.objects.filter(
                location_letter=letter, location_number=number
            ).only("id", "name", "quantity", "location_shelf", "category", "is_active")
        elif letter:
            items = InventoryItem.objects.filter(location_letter=letter)
        elif number:
            items = InventoryItem.objects.filter(location_number=number)
        else:
            items = InventoryItem.objects.filter(barcode=bucket)

        items = items.order_by("name")
        return JsonResponse({
            "items": [
                {
                    "id": it.id,
                    "name": it.name,
                    "quantity": it.quantity,
                    "shelf": it.location_shelf,
                    "category": str(it.category) if it.category else "",
                    "active": it.is_active,
                }
                for it in items
            ],
        })


class QRCodeListAdminView(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.filter(qr_code__isnull=False).order_by("name")
        return render(request, "inventory/barcode_list.html", {"items": items})


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------
class ItemAttachmentUploadView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "Keine Datei ausgewählt.")
            return redirect("edit-item", pk=item_id)

        if file.size > 100 * 1024 * 1024:
            messages.error(request, "Datei zu groß (max. 100 MB).")
            return redirect("edit-item", pk=item_id)

        ItemAttachment.objects.create(item=item, uploaded_by=request.user, file=file)
        messages.success(request, "Anhang hochgeladen.")
        return redirect("edit-item", pk=item_id)


class ItemAttachmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, attachment_id):
        attachment = get_object_or_404(ItemAttachment, pk=attachment_id)
        item_id = attachment.item_id
        attachment.delete()
        messages.success(request, "Anhang gelöscht.")
        return redirect("edit-item", pk=item_id)


# ---------------------------------------------------------------------------
# Item Comments
# ---------------------------------------------------------------------------
class ItemCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        form = ItemCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.item = item
            comment.author = request.user
            comment.save()
            messages.success(request, "Kommentar hinzugefügt.")
        else:
            messages.error(request, "Fehler beim Speichern des Kommentars.")
        return redirect("edit-item", pk=item_id)


__all__ = [
    "MarkItemAPI", "QuickAdjustQuantityView", "NFCItemRedirectView",
    "NFCStorageLocationView", "DrawerItemsAPI", "QRCodeListAdminView",
    "ItemAttachmentUploadView", "ItemAttachmentDeleteView", "ItemCommentCreateView",
]
