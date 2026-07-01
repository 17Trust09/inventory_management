"""
Dashboard-Views: Übersicht, Dashboard-Selector und Favoriten.
"""
from collections import defaultdict
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum, Prefetch
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from ..feature_flags import get_feature_flags
from ..models import (
    InventoryItem,
    InventoryHistory,
    Category,
    UserProfile,
    BorrowedItem,
    TagType,
    ApplicationTag,
    StorageLocation,
    Overview,
    Feedback,
)
from ..exports import EXPORT_COLUMNS
from django.shortcuts import get_object_or_404
from ..models import ItemComment
from .helpers import (
    _get_overview_and_features,
    _allowed_overviews_for_user,
    safe_redirect_or,
    extract_next,
    _feature_enabled,
)


# ---------------------------------------------------------------------------
# Dashboard-Selector
# ---------------------------------------------------------------------------
class DashboardSelectorView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/dashboard_selector.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        allowed = _allowed_overviews_for_user(self.request.user)
        overviews = list(allowed)
        ctx["overviews"] = overviews
        if _feature_enabled("show_favorites"):
            profile = UserProfile.objects.filter(user=self.request.user).first()
            favorite_ids = set(
                profile.favorite_overviews.values_list("id", flat=True)
            ) if profile else set()
            ctx["favorite_overviews"] = [ov for ov in overviews if ov.id in favorite_ids]
            ctx["favorite_overview_ids"] = favorite_ids
        else:
            ctx["favorite_overviews"] = []
            ctx["favorite_overview_ids"] = set()
        if _feature_enabled("show_feedback"):
            ctx["latest_feedback"] = list(Feedback.objects.order_by("-created_at")[:3])
        else:
            ctx["latest_feedback"] = []
        return ctx


def dashboards(request):
    """Kompatibilitäts-Route: gleiche Filterung wie oben."""
    allowed = _allowed_overviews_for_user(request.user)
    overviews = (
        allowed.prefetch_related(
            Prefetch("categories", queryset=Category.objects.only("id", "name").order_by("name"))
        )
        .order_by("order", "name")
        .distinct()
    )
    return render(request, "inventory/dashboards.html", {"overviews": overviews})


# ---------------------------------------------------------------------------
# Overview-Dashboard – Kern-Ansicht
# ---------------------------------------------------------------------------
class OverviewDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/overview_dashboard.html"

    SORT_MAP = {
        "name": "name",
        "category": "category__name",
        "location": "storage_location__name",
        "quantity": "quantity",
        "min": "low_quantity",
        "borrowed": "borrowed_open",
    }
    DEFAULT_SORT = "name"

    def dispatch(self, request, *args, **kwargs):
        self.overview = get_object_or_404(Overview, slug=kwargs["slug"], is_active=True)
        if not request.user.is_superuser:
            profile = UserProfile.objects.filter(user=request.user).first()
            allowed = profile.allowed_overviews.filter(pk=self.overview.pk).exists() if profile else False
            if not allowed:
                messages.error(request, "Du hast keinen Zugriff auf dieses Dashboard.")
                return redirect("dashboards")
        return super().dispatch(request, *args, **kwargs)

    def base_queryset(self):
        open_borrowings = Prefetch(
            "borrowings",
            queryset=BorrowedItem.objects.filter(returned=False),
            to_attr="prefetched_open_borrowings",
        )
        comment_prefetch = Prefetch(
            "comments",
            queryset=ItemComment.objects.select_related("author").order_by("-updated_at", "-created_at"),
            to_attr="prefetched_comments",
        )
        prefetches = ["application_tags", open_borrowings]
        if self.overview.enable_comments:
            prefetches.append(comment_prefetch)
        qs = (
            InventoryItem.objects
            .filter(overview=self.overview)
            .select_related("category", "storage_location", "user")
            .prefetch_related(*prefetches)
            .annotate(
                borrowed_open=Sum(
                    "borrowings__quantity_borrowed",
                    filter=Q(borrowings__returned=False)
                )
            )
        )
        return qs

    def apply_filters(self, qs):
        request = self.request
        q = request.GET.get("q", "").strip()
        category_id = request.GET.get("category", "").strip()
        tag_name = request.GET.get("tag", "").strip()
        storage_location_id = request.GET.get("storage_location", "").strip()
        loc_letter = request.GET.get("location_letter", "").strip()
        loc_number = request.GET.get("location_number", "").strip()
        only_low = request.GET.get("only_low", "") == "1"

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(barcode__icontains=q)
                | Q(location_letter__icontains=q)
                | Q(location_number__icontains=q)
            )
        if category_id and category_id != "all":
            qs = qs.filter(category_id=category_id)
        if tag_name and tag_name != "all":
            qs = qs.filter(application_tags__name=tag_name)
        if storage_location_id:
            qs = qs.filter(storage_location_id=storage_location_id)
        if loc_letter:
            qs = qs.filter(location_letter__iexact=loc_letter)
        if loc_number:
            qs = qs.filter(location_number__iexact=loc_number)
        if only_low and self.overview.has_min_stock:
            qs = qs.filter(quantity__lt=F("low_quantity"))
        return qs.distinct()

    def apply_sort(self, qs):
        sort_key = self.request.GET.get("sort", self.DEFAULT_SORT)
        order = self.request.GET.get("order", "asc")
        field = self.SORT_MAP.get(sort_key, self.SORT_MAP[self.DEFAULT_SORT])
        if order == "desc":
            field = f"-{field}"
        return qs.order_by(field), sort_key, order

    def get_auxiliary_choices(self):
        cats = list(self.overview.categories.all())
        if not cats:
            cats = list(Category.objects.all().order_by("name"))
        try:
            tagtype_name = "Verbrauchsmaterial" if self.overview.is_consumable_mode else "Equipment"
            tt = TagType.objects.get(name=tagtype_name)
            tags = list(ApplicationTag.objects.filter(type=tt).order_by("name"))
        except TagType.DoesNotExist:
            tags = list(ApplicationTag.objects.all().order_by("name"))
        return cats, tags

    def _compute_add_url(self):
        if self.overview.is_consumable_mode:
            return reverse("add-consumable")
        return reverse("add-equipment")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        features = self.overview.features()
        base_qs = self.base_queryset()
        qs = base_qs
        if features.get("enable_advanced_filters", True):
            qs = self.apply_filters(qs)
        qs, sort_key, order = self.apply_sort(qs)

        try:
            per_page = int(self.request.GET.get("page_size", "25"))
        except ValueError:
            per_page = 25
        per_page = max(5, min(per_page, 200))
        paginator = Paginator(qs, per_page)
        page_number = self.request.GET.get("page", "1")
        page_obj = paginator.get_page(page_number)

        def next_order_for(col):
            if sort_key == col and order == "asc":
                return "desc"
            return "asc"

        cats, tags = self.get_auxiliary_choices()
        storage_locations = list(
            StorageLocation.objects.filter(items__overview=self.overview)
            .distinct()
        )
        storage_locations.sort(key=lambda loc: loc.get_full_path().lower())

        favorites = []
        overview_is_favorite = False
        if _feature_enabled("show_favorites"):
            favorites = list(
                InventoryItem.objects
                .filter(overview=self.overview, is_favorite=True)
                .only("id", "name", "overview")
                .order_by("name")[:6]
            )
            profile = UserProfile.objects.filter(user=self.request.user).first()
            overview_is_favorite = bool(
                profile and profile.favorite_overviews.filter(pk=self.overview.pk).exists()
            )

        ctx.update({
            "overview": self.overview,
            "features": features,
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "per_page": per_page,
            "q": self.request.GET.get("q", "").strip() if features.get("enable_advanced_filters", True) else "",
            "selected_category": self.request.GET.get("category", "") if features.get("enable_advanced_filters", True) else "",
            "selected_tag": self.request.GET.get("tag", "") if features.get("enable_advanced_filters", True) else "",
            "selected_storage_location": self.request.GET.get("storage_location", "") if features.get("enable_advanced_filters", True) else "",
            "location_letter": self.request.GET.get("location_letter", "") if features.get("enable_advanced_filters", True) else "",
            "location_number": self.request.GET.get("location_number", "") if features.get("enable_advanced_filters", True) else "",
            "only_low": self.request.GET.get("only_low", "") == "1" if features.get("enable_advanced_filters", True) else False,
            "sort_key": sort_key,
            "order": order,
            "next_order": {col: next_order_for(col) for col in self.SORT_MAP},
            "categories": cats,
            "tags": tags,
            "storage_locations": storage_locations,
            "add_url": self._compute_add_url(),
            "export_csv_url": reverse("overview-export", kwargs={"slug": self.overview.slug, "export_format": "csv"}),
            "export_excel_url": reverse("overview-export", kwargs={"slug": self.overview.slug, "export_format": "excel"}),
            "export_columns": [(key, label) for key, label, _ in EXPORT_COLUMNS],
            "favorites": favorites,
            "overview_is_favorite": overview_is_favorite,
            "breadcrumbs": [
                {"name": "Dashboards", "url": reverse("dashboards")},
                {"name": f"{self.overview.icon_emoji} {self.overview.name}", "url": None},
            ],
        })
        return ctx


# ---------------------------------------------------------------------------
# Favoriten-Toggle
# ---------------------------------------------------------------------------
class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        if not get_feature_flags().get("show_favorites", True):
            messages.error(request, "Favoriten sind aktuell deaktiviert.")
            return redirect("dashboards")
        item = get_object_or_404(InventoryItem, pk=item_id)
        item.is_favorite = not item.is_favorite
        item.save(update_fields=["is_favorite"])
        status = "⭐" if item.is_favorite else "☆"
        messages.success(request, f"{status} Favoriten-Status für „{item.name}“ geändert.")
        nxt = extract_next(request)
        return safe_redirect_or(request, nxt, fallback_view="dashboards")


class ToggleOverviewFavoriteView(LoginRequiredMixin, View):
    def post(self, request, slug):
        if not get_feature_flags().get("show_favorites", True):
            messages.error(request, "Favoriten sind aktuell deaktiviert.")
            return redirect("dashboards")
        overview = get_object_or_404(Overview, slug=slug, is_active=True)
        profile = UserProfile.objects.get_or_create(user=request.user)[0]
        if profile.favorite_overviews.filter(pk=overview.pk).exists():
            profile.favorite_overviews.remove(overview)
            messages.success(request, f"Dashboard „{overview.name}“ aus Favoriten entfernt.")
        else:
            profile.favorite_overviews.add(overview)
            messages.success(request, f"⭐ Dashboard „{overview.name}“ als Favorit markiert.")
        return redirect("dashboards")


__all__ = [
    "DashboardSelectorView",
    "dashboards",
    "OverviewDashboardView",
    "ToggleFavoriteView",
    "ToggleOverviewFavoriteView",
]
