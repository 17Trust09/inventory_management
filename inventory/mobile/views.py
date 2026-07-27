from django.shortcuts import render as django_render

from inventory import views
from inventory.views import items as item_views_module

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.forms import modelform_factory
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from inventory.models import ApplicationTag, Category, InventoryItem, StorageLocation
from inventory.views.helpers import _allowed_overviews_for_user


def _existing_model_fields(model, field_names):
    """Return field names that exist on the currently deployed model."""
    available = {field.name for field in model._meta.get_fields()}
    return [field_name for field_name in field_names if field_name in available]


class MobileMasterDataFormMixin:
    fields = ["name"]
    success_url_name = None
    delete_url_name = None
    page_title = "Stammdaten"
    page_name = "settings"

    def get_form_class(self):
        return modelform_factory(self.model, fields=_existing_model_fields(self.model, self.fields))

    def get_success_url(self):
        return reverse_lazy(self.success_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.page_title,
                "page_name": self.page_name,
                "cancel_url": reverse_lazy(self.success_url_name),
            }
        )
        if getattr(self.object, "pk", None) and self.delete_url_name:
            context["delete_url"] = reverse_lazy(self.delete_url_name, kwargs={"pk": self.object.pk})
        return context


class MobileCategoryListView(LoginRequiredMixin, ListView):
    template_name = "mobile/categories.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.annotate(item_count=Count("inventoryitem", distinct=True)).order_by("name")


class MobileCategoryCreateView(LoginRequiredMixin, MobileMasterDataFormMixin, CreateView):
    model = Category
    template_name = "mobile/category_form.html"
    fields = ["name", "icon_emoji"]
    success_url_name = "mobile-categories"
    delete_url_name = "mobile-category-delete"
    page_title = "Kategorie anlegen"


class MobileCategoryUpdateView(LoginRequiredMixin, MobileMasterDataFormMixin, UpdateView):
    model = Category
    template_name = "mobile/category_form.html"
    fields = ["name", "icon_emoji"]
    success_url_name = "mobile-categories"
    delete_url_name = "mobile-category-delete"
    page_title = "Kategorie bearbeiten"


class MobileCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    success_url = reverse_lazy("mobile-categories")


def _application_tag_type_field():
    return "tag_type" if _existing_model_fields(ApplicationTag, ["tag_type"]) else "type"


class MobileTagListView(LoginRequiredMixin, ListView):
    template_name = "mobile/tags.html"
    context_object_name = "tags"

    def get_queryset(self):
        tag_type_field = _application_tag_type_field()
        return (
            ApplicationTag.objects.select_related(tag_type_field)
            .annotate(item_count=Count("inventoryitem", distinct=True))
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tag_type_field"] = _application_tag_type_field()
        return context


class MobileTagCreateView(LoginRequiredMixin, MobileMasterDataFormMixin, CreateView):
    model = ApplicationTag
    template_name = "mobile/tag_form.html"
    success_url_name = "mobile-tags"
    delete_url_name = "mobile-tag-delete"
    page_title = "Tag anlegen"

    def get_form_class(self):
        return modelform_factory(ApplicationTag, fields=["name", _application_tag_type_field()])


class MobileTagUpdateView(LoginRequiredMixin, MobileMasterDataFormMixin, UpdateView):
    model = ApplicationTag
    template_name = "mobile/tag_form.html"
    success_url_name = "mobile-tags"
    delete_url_name = "mobile-tag-delete"
    page_title = "Tag bearbeiten"

    def get_form_class(self):
        return modelform_factory(ApplicationTag, fields=["name", _application_tag_type_field()])


class MobileTagDeleteView(LoginRequiredMixin, DeleteView):
    model = ApplicationTag
    success_url = reverse_lazy("mobile-tags")


class MobileLocationListView(LoginRequiredMixin, ListView):
    template_name = "mobile/locations.html"
    context_object_name = "locations"

    def get_queryset(self):
        return (
            StorageLocation.objects.filter(parent__isnull=True)
            .prefetch_related("children")
            .annotate(item_count=Count("items", distinct=True), child_count=Count("children", distinct=True))
            .order_by("name")
        )


class MobileLocationCreateView(LoginRequiredMixin, MobileMasterDataFormMixin, CreateView):
    model = StorageLocation
    template_name = "mobile/location_form.html"
    fields = ["name", "parent"]
    success_url_name = "mobile-locations"
    delete_url_name = "mobile-location-delete"
    page_title = "Lagerort anlegen"


class MobileLocationUpdateView(LoginRequiredMixin, MobileMasterDataFormMixin, UpdateView):
    model = StorageLocation
    template_name = "mobile/location_form.html"
    fields = ["name", "parent"]
    success_url_name = "mobile-locations"
    delete_url_name = "mobile-location-delete"
    page_title = "Lagerort bearbeiten"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if "parent" in form.fields and self.object.pk:
            form.fields["parent"].queryset = StorageLocation.objects.exclude(pk=self.object.pk).order_by("name")
        return form


class MobileLocationDeleteView(LoginRequiredMixin, DeleteView):
    model = StorageLocation
    success_url = reverse_lazy("mobile-locations")


class MobileSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "mobile/settings.html"


class MobileScanView(LoginRequiredMixin, TemplateView):
    template_name = "mobile/scan.html"


class MobileSearchView(LoginRequiredMixin, TemplateView):
    template_name = "mobile/search.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        ctx["q"] = query
        ctx["items"] = []
        if query:
            overviews = _allowed_overviews_for_user(self.request.user)
            ctx["items"] = (
                InventoryItem.objects.filter(overview__in=overviews)
                .filter(
                    Q(name__icontains=query)
                    | Q(barcode__icontains=query)
                    | Q(category__name__icontains=query)
                    | Q(storage_location__name__icontains=query)
                    | Q(application_tags__name__icontains=query)
                )
                .select_related("overview", "category", "storage_location")
                .prefetch_related("application_tags")
                .distinct()
                .order_by("name")[:50]
            )
        return ctx


def mobile_render(request, template_name, context=None, *args, **kwargs):
    if template_name == "inventory/item_form.html":
        template_name = "mobile/item_form.html"
    return django_render(request, template_name, context, *args, **kwargs)


class MobileItemRenderMixin:
    def _with_mobile_item_template(self, method, request, *args, **kwargs):
        original_render = item_views_module.render
        item_views_module.render = mobile_render
        try:
            return method(request, *args, **kwargs)
        finally:
            item_views_module.render = original_render


class MobileAddEquipmentItem(MobileItemRenderMixin, views.AddEquipmentItem):
    def get(self, request):
        return self._with_mobile_item_template(super().get, request)

    def post(self, request):
        return self._with_mobile_item_template(super().post, request)


class MobileAddConsumableItem(MobileItemRenderMixin, views.AddConsumableItem):
    def get(self, request):
        return self._with_mobile_item_template(super().get, request)

    def post(self, request):
        return self._with_mobile_item_template(super().post, request)


class MobileEditItem(views.EditItem):
    template_name = "mobile/item_form.html"
