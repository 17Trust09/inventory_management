"""
Admin-Items: Liste, Edit, Delete, BorrowedItems, QR-Codes.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView
from django.contrib import messages
from django.http import HttpResponseBadRequest

from ..models import InventoryItem, BorrowedItem
from .helpers import staff_required, StaffRequiredMixin


class InventoryItemListView(StaffRequiredMixin, ListView):
    model = InventoryItem
    template_name = 'inventory/admin_items_list.html'
    context_object_name = 'items'


class BorrowedItemListView(StaffRequiredMixin, ListView):
    model = BorrowedItem
    template_name = 'inventory/admin_borrowed_items_list.html'
    context_object_name = 'borrowed_items'


@staff_required
def admin_item_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    # Simplify: Redirect to the existing edit-item view
    return redirect('edit-item', pk=pk)


@staff_required
def admin_item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == "POST":
        name = item.name
        item.delete()
        messages.success(request, f"Artikel „{name}“ gelöscht.")
        return redirect('admin_items')
    return render(request, 'inventory/admin_item_confirm_delete.html', {'item': item})


@staff_required
def admin_qr_codes_view(request):
    from ..models import QRCodeOverviewModel
    qr_overviews = QRCodeOverviewModel.objects.all()
    return render(request, 'inventory/admin_qr_overview.html', {"qr_overviews": qr_overviews})
