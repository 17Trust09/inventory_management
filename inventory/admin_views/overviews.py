"""
Admin-Overviews: List, Create, Edit, Delete, Approve.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages

from ..forms import OverviewForm
from ..models import Overview
from .helpers import staff_required, StaffRequiredMixin


class OverviewListView(StaffRequiredMixin, ListView):
    model = Overview
    template_name = 'inventory/admin_overviews_list.html'
    context_object_name = 'overviews'


@staff_required
def admin_overview_create(request):
    if request.method == "POST":
        form = OverviewForm(request.POST)
        if form.is_valid():
            overview = form.save()
            messages.success(request, f"Dashboard „{overview.name}“ angelegt.")
            return redirect('admin_overviews')
    else:
        form = OverviewForm()
    return render(request, 'inventory/admin_overview_form.html', {
        "form": form,
        "title": "Dashboard anlegen",
    })


@staff_required
def admin_overview_edit(request, pk):
    overview = get_object_or_404(Overview, pk=pk)
    if request.method == "POST":
        form = OverviewForm(request.POST, instance=overview)
        if form.is_valid():
            overview = form.save()
            messages.success(request, f"Dashboard „{overview.name}“ gespeichert.")
            return redirect('admin_overviews')
    else:
        form = OverviewForm(instance=overview)
    return render(request, 'inventory/admin_overview_form.html', {
        "form": form,
        "overview": overview,
        "title": f"Dashboard „{overview.name}“ bearbeiten",
    })


@staff_required
def admin_overview_delete(request, pk):
    overview = get_object_or_404(Overview, pk=pk)
    if request.method == "POST":
        name = overview.name
        overview.delete()
        messages.success(request, f"Dashboard „{name}“ gelöscht.")
        return redirect('admin_overviews')
    return render(request, 'inventory/admin_overview_confirm_delete.html', {"overview": overview})


@staff_required
def admin_overview_approve(request, pk):
    if request.method == "POST":
        overview = get_object_or_404(Overview, pk=pk)
        action = request.POST.get("action")
        if action == "approve":
            overview.is_active = True
            overview.save(update_fields=["is_active"])
            messages.success(request, f"Dashboard „{overview.name}“ freigegeben.")
        elif action == "reject":
            name = overview.name
            overview.delete()
            messages.success(request, f"Dashboard-Anfrage „{name}“ abgelehnt und gelöscht.")
        return redirect('admin_dashboard')
    return redirect('admin_dashboard')
