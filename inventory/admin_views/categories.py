"""
Admin-Kategorien: Übersicht + CRUD.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib import messages

from ..models import Category
from .helpers import staff_required, StaffRequiredMixin, CategoryForm


@staff_required
def admin_categories_overview(request):
    categories = Category.objects.all().order_by("name")
    return render(request, 'inventory/admin_categories_overview.html', {"categories": categories})


class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/admin_category_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Kategorie „{self.object.name}“ angelegt.")
        return reverse('admin_categories')


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/admin_category_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Kategorie „{self.object.name}“ gespeichert.")
        return reverse('admin_categories')


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/admin_category_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"Kategorie „{self.object.name}“ gelöscht.")
        return reverse('admin_categories')


# ---------------------------------------------------------------------------
# Pending-Kategorie-Anfrage: Freigabe / Ablehnen
# ---------------------------------------------------------------------------
@staff_required
def admin_pending_category_approve(request, pk):
    from ..models import PendingCategoryRequest, Category
    pending = get_object_or_404(PendingCategoryRequest, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            Category.objects.get_or_create(name=pending.name)
            pending.approved = True
            pending.save()
            messages.success(request, f"Kategorie „{pending.name}“ freigegeben und angelegt.")
        elif action == "reject":
            pending.approved = False
            pending.save()
            messages.success(request, f"Kategorie-Anfrage „{pending.name}“ abgelehnt.")
        return redirect('admin_dashboard')
    return redirect('admin_dashboard')
