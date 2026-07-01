"""
Borrowed-Items-Views: Ausleihen und Rückgabe.
"""
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum, Prefetch

from ..forms import BorrowItemForm
from ..models import InventoryItem, BorrowedItem
from .helpers import _snapshot_item, _create_history_entry
from ..models import InventoryHistory


class BorrowedItemsView(LoginRequiredMixin, View):
    def get(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        form = BorrowItemForm()
        return render(request, "inventory/borrow_item.html", {
            "item": item,
            "form": form,
            "breadcrumbs": [
                {"name": "Dashboards", "url": reverse("dashboards")},
                {"name": item.name, "url": reverse("edit-item", kwargs={"pk": item.pk})},
                {"name": "Ausleihen", "url": None},
            ],
        })

    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, pk=item_id)
        form = BorrowItemForm(request.POST)
        if form.is_valid():
            borrowed = form.save(commit=False)
            borrowed.item = item
            borrowed.save()
            item.quantity -= borrowed.quantity_borrowed
            item.save(update_fields=["quantity"])
            messages.success(
                request,
                f"{borrowed.quantity_borrowed}x „{item.name}“ an {borrowed.borrower} ausgeliehen.",
            )
            if item.overview:
                return redirect("overview-dashboard", slug=item.overview.slug)
            return redirect("dashboards")
        return render(request, "inventory/borrow_item.html", {
            "item": item,
            "form": form,
        })


class ReturnItemView(LoginRequiredMixin, View):
    def post(self, request, borrow_id):
        borrowed = get_object_or_404(BorrowedItem, pk=borrow_id, returned=False)
        item = borrowed.item
        borrowed.returned = True
        borrowed.save()
        item.quantity += borrowed.quantity_borrowed
        item.save(update_fields=["quantity"])

        _create_history_entry(
            item=item,
            user=request.user,
            action=InventoryHistory.Action.ADJUSTED,
            before={"quantity": item.quantity - borrowed.quantity_borrowed},
            after={"quantity": item.quantity},
            meta={"source": "return"},
        )
        messages.success(request, f"„{item.name}“ zurückerhalten.")
        if item.overview:
            return redirect("overview-dashboard", slug=item.overview.slug)
        return redirect("dashboards")


__all__ = ["BorrowedItemsView", "ReturnItemView"]
