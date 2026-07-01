"""
Admin-History: Liste und Rollback.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages

from ..models import InventoryHistory, InventoryItem
from .helpers import staff_required


@staff_required
def admin_history_list(request):
    action = request.GET.get("action", "")
    items = InventoryHistory.objects.select_related("item", "user").order_by("-created_at")
    if action:
        items = items.filter(action=action)
    return render(request, 'inventory/admin_history_list.html', {
        "history_items": items[:200],
        "actions": InventoryHistory.Action.choices,
        "selected_action": action,
    })


@staff_required
def admin_history_rollback(request, pk):
    entry = get_object_or_404(InventoryHistory.objects.select_related("item"), pk=pk)
    item = entry.item
    data_after = entry.data_after
    if not data_after:
        messages.error(request, "Dieser Eintrag enthält keine Wiederherstellungsdaten.")
        return redirect("admin_history_list")
    for field, value in data_after.items():
        if field == "tags":
            from ..models import ApplicationTag
            if value:
                item.application_tags.set(value)
            else:
                item.application_tags.clear()
            continue
        if field == "maintenance_date":
            from datetime import date
            item.maintenance_date = date.fromisoformat(value) if value else None
            continue
        if hasattr(item, field) and field not in ("id",):
            setattr(item, field, value)
    item.save()
    messages.success(request, f"Artikel „{item.name}“ zurückgesetzt (Stand: {entry.created_at.strftime('%d.%m.%Y %H:%M')}).")
    return redirect("admin_history_list")
