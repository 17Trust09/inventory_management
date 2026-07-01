"""
Admin-Tags: Übersicht + CRUD + TagType CRUD.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages

from ..models import ApplicationTag, TagType
from .helpers import staff_required, StaffRequiredMixin


@staff_required
def admin_tags_overview(request):
    tags = ApplicationTag.objects.select_related("type").order_by("type__name", "name")
    tag_types = TagType.objects.all().order_by("name")
    return render(request, 'inventory/admin_tags_overview.html', {
        "tags": tags,
        "tag_types": tag_types,
    })


# ---------------------------------------------------------------------------
# ApplicationTag CRUD
# ---------------------------------------------------------------------------
class ApplicationTagCreateView(StaffRequiredMixin, CreateView):
    model = ApplicationTag
    fields = ['name']
    template_name = 'inventory/admin_tag_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ angelegt.")
        return reverse('admin_tags_overview')


class ApplicationTagUpdateView(StaffRequiredMixin, UpdateView):
    model = ApplicationTag
    fields = ['name']
    template_name = 'inventory/admin_tag_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ gespeichert.")
        return reverse('admin_tags_overview')


class ApplicationTagDeleteView(StaffRequiredMixin, DeleteView):
    model = ApplicationTag
    template_name = 'inventory/admin_tag_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"Tag „{self.object.name}“ gelöscht.")
        return reverse('admin_tags_overview')


# ---------------------------------------------------------------------------
# TagType CRUD
# ---------------------------------------------------------------------------
class TagTypeListView(StaffRequiredMixin, ListView):
    model = TagType
    template_name = 'inventory/admin_tagtypes_list.html'
    context_object_name = 'tag_types'


class TagTypeCreateView(StaffRequiredMixin, CreateView):
    model = TagType
    fields = ['name']
    template_name = 'inventory/admin_tagtype_form.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ angelegt.")
        return reverse('admin_tagtypes')


class TagTypeUpdateView(StaffRequiredMixin, UpdateView):
    model = TagType
    fields = ['name']
    template_name = 'inventory/admin_tagtype_form.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ gespeichert.")
        return reverse('admin_tagtypes')


class TagTypeDeleteView(StaffRequiredMixin, DeleteView):
    model = TagType
    template_name = 'inventory/admin_tagtype_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, f"TagType „{self.object.name}“ gelöscht.")
        return reverse('admin_tagtypes')
