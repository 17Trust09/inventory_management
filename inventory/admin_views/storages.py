"""
Admin-StorageLocations: List + CRUD + NFC.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
import uuid

from ..models import StorageLocation
from ..forms import StorageLocationForm
from .helpers import StaffRequiredMixin


class StorageLocationListView(StaffRequiredMixin, ListView):
    model = StorageLocation
    template_name = 'inventory/admin_storagelocations_list.html'
    context_object_name = 'locations'


class StorageLocationCreateView(StaffRequiredMixin, CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/admin_storagelocation_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_create'] = True
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Lagerort angelegt.")
        return reverse('admin_storagelocations')


class StorageLocationUpdateView(StaffRequiredMixin, UpdateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/admin_storagelocation_form.html'

    def get_success_url(self):
        messages.success(self.request, "Lagerort gespeichert.")
        return reverse('admin_storagelocations')


class StorageLocationDeleteView(StaffRequiredMixin, DeleteView):
    model = StorageLocation
    template_name = 'inventory/admin_storagelocation_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, "Lagerort gelöscht.")
        return reverse('admin_storagelocations')


def admin_storagelocation_regenerate_nfc(request, pk):
    if request.method != "POST":
        return redirect('admin_storagelocations')
    loc = get_object_or_404(StorageLocation, pk=pk)
    loc.nfc_token = str(uuid.uuid4())
    loc.save(update_fields=["nfc_token"])
    messages.success(request, f"NFC-Token für „{loc.name}“ neu generiert.")
    return redirect('admin_storagelocations')
