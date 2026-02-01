from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from .models import ScheduledExport

from .models import InventoryItem, Overview


EXPORT_COLUMNS = [
    ("id", "ID", lambda it: it.id),
    ("name", "Name", lambda it: it.name),
    ("type", "Typ", lambda it: it.get_item_type_display()),
    ("quantity", "Bestand", lambda it: it.quantity),
    ("unit", "Einheit", lambda it: it.get_unit_display() if it.unit else ""),
    ("variant", "Variante", lambda it: it.variant or ""),
    ("category", "Kategorie", lambda it: it.category.name if it.category else ""),
    ("storage_location", "Lagerort", lambda it: it.storage_location.get_full_path() if it.storage_location else ""),
    ("location_letter", "Ort (Buchstabe)", lambda it: it.location_letter or ""),
    ("location_number", "Ort (Nummer)", lambda it: it.location_number or ""),
    ("location_shelf", "Ort (Fach)", lambda it: it.location_shelf or ""),
    ("min_stock", "Mindestbestand", lambda it: it.low_quantity),
    ("tags", "Tags", lambda it: ", ".join(sorted(it.application_tags.values_list("name", flat=True)))),
    ("overview", "Dashboard", lambda it: it.overview.name if it.overview else ""),
    ("maintenance_date", "Wartungsdatum", lambda it: it.maintenance_date.isoformat() if it.maintenance_date else ""),
    ("last_used", "Letzte Nutzung", lambda it: it.last_used.isoformat() if it.last_used else ""),
    ("created_at", "Erstellt am", lambda it: it.date_created.isoformat() if it.date_created else ""),
]


def get_export_columns(selected: Iterable[str] | None = None):
    if selected:
        selected_set = set(selected)
        return [col for col in EXPORT_COLUMNS if col[0] in selected_set]
    return EXPORT_COLUMNS[:]


def calculate_next_run(frequency: str, base_time=None):
    base = base_time or timezone.now()
    if frequency == ScheduledExport.Frequency.DAILY:
        return base + timedelta(days=1)
    if frequency == ScheduledExport.Frequency.WEEKLY:
        return base + timedelta(days=7)
    return base + timedelta(days=30)


def export_overview_to_file(
    *,
    overview: Overview,
    export_format: str,
    columns: Iterable[str] | None = None,
) -> str:
    selected_columns = get_export_columns(columns)
    delimiter = ";" if export_format == "csv" else "\t"
    extension = "csv" if export_format == "csv" else "xls"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"overview_{overview.slug}_{timestamp}.{extension}"

    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)
    full_path = os.path.join(export_dir, filename)

    items = (
        InventoryItem.objects.filter(overview=overview)
        .select_related("category", "storage_location", "overview")
        .prefetch_related("application_tags")
        .order_by("name")
    )

    with open(full_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow([col[1] for col in selected_columns])
        for item in items:
            writer.writerow([col[2](item) for col in selected_columns])

    return os.path.join("exports", filename)
