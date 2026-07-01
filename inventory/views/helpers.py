"""
Hilfsfunktionen für alle View-Module.
Enthält Redirect-Helper, Snapshot-Logik und Overview-Zugriff.
"""
import csv
import os
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db.models import Q, F, Sum, Prefetch
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.contrib.auth.models import User, Group

from ..feature_flags import get_feature_flags
from ..models import (
    InventoryItem,
    InventoryHistory,
    ItemAttachment,
    ItemComment,
    Category,
    UserProfile,
    BorrowedItem,
    TagType,
    ApplicationTag,
    StorageLocation,
    GlobalSettings,
    Overview,
    ScheduledExport,
    ExportRun,
)


def safe_redirect_or(request, url, fallback_view=None, fallback_kwargs=None):
    """
    Validiert eine Benutzer-gesteuerte Redirect-URL (next / HTTP_REFERER)
    und leitet entweder dorthin oder per View-Name + kwargs weiter.
    """
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(url)
    if fallback_view:
        return redirect(fallback_view, **(fallback_kwargs or {}))
    return redirect("/")


def extract_next(request):
    """Extrahiert 'next' aus POST, GET oder HTTP_REFERER."""
    return request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER", "")


def _get_overview_and_features(request, default_item_type: str):
    slug = request.GET.get("o") or request.POST.get("o")
    ov = None
    from types import SimpleNamespace
    features = SimpleNamespace(
        show_quantity=True,
        has_min_stock=True,
        has_locations=True,
        enable_borrow=True,
        require_qr=False,
        is_consumable_mode=(default_item_type == "consumable"),
        enable_comments=False,
        show_order_button=False,
    )
    if slug:
        try:
            ov = Overview.objects.get(slug=slug, is_active=True)
            features = ov.features()
        except Overview.DoesNotExist:
            ov = None
    return ov, features, slug


def _allowed_overviews_for_user(user):
    """Erlaubte Overviews – Superuser alle, sonst nur explizit freigegebene."""
    base_qs = Overview.objects.filter(is_active=True).order_by("order", "name")
    if not user.is_authenticated:
        return base_qs.none()
    if user.is_superuser:
        return base_qs
    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        return base_qs.none()
    allowed_ids = list(profile.allowed_overviews.values_list("id", flat=True))
    if not allowed_ids:
        return base_qs.none()
    return base_qs.filter(id__in=allowed_ids)


def _resolve_nfc_base_url(request, base_choice: str) -> str:
    gs = GlobalSettings.objects.first()
    local_base = gs.nfc_base_url_local if gs else ""
    remote_base = gs.nfc_base_url_remote if gs else ""
    base = local_base if base_choice == "local" else remote_base
    if not base:
        return request.build_absolute_uri("/").rstrip("/")
    return base.rstrip("/")


# ---------------------------------------------------------------------------
# History / Snapshot Helper
# ---------------------------------------------------------------------------
HISTORY_FIELDS = (
    "name",
    "description",
    "quantity",
    "unit",
    "variant",
    "category_id",
    "storage_location_id",
    "location_letter",
    "location_number",
    "location_shelf",
    "low_quantity",
    "order_link",
    "maintenance_date",
    "overview_id",
    "item_type",
    "is_active",
    "tags",
)

HISTORY_LABELS = {
    "name": "Name",
    "description": "Beschreibung",
    "quantity": "Bestand",
    "unit": "Einheit",
    "variant": "Variante",
    "category_id": "Kategorie",
    "storage_location_id": "Lagerort",
    "location_letter": "Ort (Buchstabe)",
    "location_number": "Ort (Nummer)",
    "location_shelf": "Ort (Fach)",
    "low_quantity": "Mindestbestand",
    "order_link": "Bestell-Link",
    "maintenance_date": "Wartungs-/Ablaufdatum",
    "overview_id": "Dashboard",
    "item_type": "Typ",
    "is_active": "Aktiv",
    "tags": "Tags",
}

MOVEMENT_FIELDS = {
    "storage_location_id",
    "location_letter",
    "location_number",
    "location_shelf",
}


def _snapshot_item(item: InventoryItem) -> dict:
    return {
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "unit": item.unit,
        "variant": item.variant,
        "category_id": item.category_id,
        "storage_location_id": item.storage_location_id,
        "location_letter": item.location_letter,
        "location_number": item.location_number,
        "location_shelf": item.location_shelf,
        "low_quantity": item.low_quantity,
        "order_link": item.order_link,
        "maintenance_date": item.maintenance_date.isoformat() if item.maintenance_date else None,
        "overview_id": item.overview_id,
        "item_type": item.item_type,
        "is_active": item.is_active,
        "tags": sorted(item.application_tags.values_list("id", flat=True)),
    }


def _format_bool(value):
    if value is True:
        return "Ja"
    if value is False:
        return "Nein"
    return "–"


def _format_date(value):
    if not value:
        return "–"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.date().isoformat()
    except ValueError:
        return value


def _build_changes(before: dict, after: dict) -> list[dict]:
    category_ids = {before.get("category_id"), after.get("category_id")} - {None}
    location_ids = {before.get("storage_location_id"), after.get("storage_location_id")} - {None}
    overview_ids = {before.get("overview_id"), after.get("overview_id")} - {None}
    tag_ids = set(before.get("tags", [])) | set(after.get("tags", []))

    categories = {c.id: c.name for c in Category.objects.filter(id__in=category_ids)}
    locations = {l.id: l.get_full_path() for l in StorageLocation.objects.filter(id__in=location_ids)}
    overviews = {o.id: o.name for o in Overview.objects.filter(id__in=overview_ids)}
    tags = {t.id: t.name for t in ApplicationTag.objects.filter(id__in=tag_ids)}

    def display_value(field: str, value):
        if field == "category_id":
            return categories.get(value, "–") if value else "–"
        if field == "storage_location_id":
            return locations.get(value, "–") if value else "–"
        if field == "overview_id":
            return overviews.get(value, "–") if value else "–"
        if field == "tags":
            return ", ".join(sorted([tags.get(tid, "–") for tid in value])) if value else "–"
        if field == "maintenance_date":
            return _format_date(value)
        if field == "is_active":
            return _format_bool(value)
        return value if value not in (None, "") else "–"

    changes = []
    for field in HISTORY_FIELDS:
        if before.get(field) != after.get(field):
            delta = None
            if field == "quantity":
                try:
                    delta = int(after.get(field) or 0) - int(before.get(field) or 0)
                except (TypeError, ValueError):
                    delta = None
            changes.append({
                "field": field,
                "label": HISTORY_LABELS.get(field, field),
                "before": display_value(field, before.get(field)),
                "after": display_value(field, after.get(field)),
                "delta": delta,
            })
    return changes


def _create_history_entry(
    *,
    item: InventoryItem,
    user,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
    changes: list | None = None,
    meta: dict | None = None,
) -> None:
    data_before = before or {}
    data_after = after or {}
    if changes is None and before is not None and after is not None:
        changes = _build_changes(before, after)
    InventoryHistory.objects.create(
        item=item,
        user=user,
        action=action,
        changes=changes or [],
        data_before=data_before,
        data_after=data_after,
        meta=meta or {},
    )


def _feature_enabled(flag_name: str) -> bool:
    return get_feature_flags().get(flag_name, True)


__all__ = [
    "safe_redirect_or", "extract_next", "_get_overview_and_features",
    "_allowed_overviews_for_user", "_resolve_nfc_base_url",
    "HISTORY_FIELDS", "HISTORY_LABELS", "MOVEMENT_FIELDS",
    "_snapshot_item", "_format_bool", "_format_date", "_build_changes",
    "_create_history_entry", "_feature_enabled",
]
