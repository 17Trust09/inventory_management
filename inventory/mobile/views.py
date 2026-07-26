from django.shortcuts import render as django_render

from inventory import views
from inventory.views import items as item_views_module

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from inventory.models import InventoryItem
from inventory.views.helpers import _allowed_overviews_for_user


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
