"""Duplicate/similar item detection helpers for inventory items."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .models import InventoryItem


def _normalise_name(value: str | None) -> str:
    return (value or "").strip().lower()


def _storage_location_path(item: InventoryItem) -> str:
    location = getattr(item, "storage_location", None)
    if not location:
        return ""
    try:
        return location.get_full_path()
    except AttributeError:
        return str(location)


def find_similar_items(name, exclude_id=None, threshold=0.85):
    """
    Find InventoryItems with similar names (ignoring storage location).
    Returns list of dicts: {id, name, quantity, storage_location_path, similarity, match_type}
    match_type: 'exact' (case-insensitive identical), 'similar' (fuzzy >= threshold), 'contains' (one contains other)
    """
    query_name = (name or "").strip()
    query_normalised = _normalise_name(query_name)
    if not query_normalised:
        return []

    qs = InventoryItem.objects.filter(is_active=True).select_related("storage_location")
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)

    matches: list[dict[str, Any]] = []
    for item in qs.only("id", "name", "quantity", "storage_location"):
        candidate_name = item.name or ""
        candidate_normalised = _normalise_name(candidate_name)
        if not candidate_normalised:
            continue

        similarity = SequenceMatcher(None, query_normalised, candidate_normalised).ratio()
        match_type = None

        if query_normalised == candidate_normalised:
            similarity = 1.0
            match_type = "exact"
        elif query_normalised in candidate_normalised or candidate_normalised in query_normalised:
            match_type = "contains"
        elif similarity >= threshold:
            match_type = "similar"

        if match_type is None:
            continue

        matches.append({
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity,
            "storage_location_path": _storage_location_path(item),
            "similarity": round(similarity, 3),
            "match_type": match_type,
        })

    matches.sort(key=lambda entry: entry["similarity"], reverse=True)
    return matches[:10]
