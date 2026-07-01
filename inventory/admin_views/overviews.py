"""
Admin-Overviews: List, Create, Edit, Delete, Approve.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView
from django.contrib import messages

from ..models import Overview
from .helpers import staff_required, StaffRequiredMixin


class OverviewListView(StaffRequiredMixin, ListView):
    model = Overview
    template_name = 'inventory/admin_overviews_list.html'
    context_object_name = 'overviews'


@staff_required
def admin_overview_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Name darf nicht leer sein.")
            return render(request, 'inventory/admin_overview_form.html')
        overview = Overview.objects.create(
            name=name,
            is_active=request.POST.get("is_active") == "1",
        )
        messages.success(request, f"Dashboard „{overview.name}“ angelegt.")
        return redirect('admin_overviews')
    return render(request, 'inventory/admin_overview_form.html')


@staff_required
def admin_overview_edit(request, pk):
    overview = get_object_or_404(Overview, pk=pk)
    if request.method == "POST":
        overview.name = request.POST.get("name", overview.name)
        overview.is_active = request.POST.get("is_active") == "1"
        overview.is_consumable_mode = request.POST.get("is_consumable_mode") == "1"
        overview.enable_comments = request.POST.get("enable_comments") == "1"
        overview.show_order_button = request.POST.get("show_order_button") == "1"
        overview.save()
        # Kategorien zuweisen
        category_ids = request.POST.getlist("categories")
        if category_ids:
            from ..models import Category
            overview.categories.set(Category.objects.filter(pk__in=category_ids))
        else:
            overview.categories.clear()
        messages.success(request, f"Dashboard „{overview.name}“ gespeichert.")
        return redirect('admin_overviews')
    from ..models import Category
    all_categories = Category.objects.all().order_by("name")
    selected_ids = set(overview.categories.values_list("id", flat=True))
    return render(request, 'inventory/admin_overview_form.html', {
        "overview": overview,
        "all_categories": all_categories,
        "selected_ids": selected_ids,
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
