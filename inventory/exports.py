from __future__ import annotations

import csv
import os
import zipfile
from datetime import datetime, timedelta
from typing import Iterable
from xml.sax.saxutils import escape

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


def _write_xlsx(path: str, rows: Iterable[Iterable[object]]) -> None:
    """Write a minimal standards-compliant .xlsx workbook without optional deps."""
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            text = "" if value is None else str(value)
            cells.append(
                f'<c r="{_xlsx_cell_ref(row_index, col_index)}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )

    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Export" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": worksheet_xml,
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content)


def _xlsx_cell_ref(row: int, col: int) -> str:
    letters = ""
    while col:
        col, remainder = divmod(col - 1, 26)
        letters = chr(65 + remainder) + letters
    return f"{letters}{row}"


def export_overview_to_file(
    overview: Overview,
    export_format: str | None = None,
    columns: Iterable[str] | None = None,
) -> str:
    if export_format is None:
        export_format = "csv"
    selected_columns = get_export_columns(columns)
    extension = "csv" if export_format == "csv" else "xlsx"
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

    if export_format == "csv":
        with open(full_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([col[1] for col in selected_columns])
            for item in items:
                writer.writerow([col[2](item) for col in selected_columns])
    else:
        rows = ([col[1] for col in selected_columns], *([col[2](item) for col in selected_columns] for item in items))
        _write_xlsx(full_path, rows)

    return os.path.join("exports", filename)
