"""Excel import/export helpers for inventory items.

The functions in this module intentionally use one stable column layout for
blank templates, backup exports, previews, and imports so files can be exported,
edited, previewed, and imported again without format conversion.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation

from .duplicate_check import find_similar_items
from .models import ApplicationTag, Category, InventoryItem, Overview, StorageLocation


BASE_COLUMNS = [
    "Name", "Dashboard", "Kategorie", "Ist-Bestand", "Einheit", "Tags",
    "Bestell-Link", "Variante", "Beschreibung",
]

FEATURE_COLUMNS = [
    ("has_min_stock", "Mindestbestand"),
    ("has_locations", "Lagerort"),
    ("enable_borrow", "Verleihbar"),
    ("show_images", "Bild-URL"),
    ("enable_comments", "Notizen"),
]

OPTIONAL_COLUMNS = [
    "Wartungsdatum",
]

def get_columns_for_overview(overview=None):
    """Spalten basierend auf Dashboard-Features."""
    cols = list(BASE_COLUMNS)
    if overview:
        for attr, name in FEATURE_COLUMNS:
            if getattr(overview, attr, False):
                cols.append(name)
    else:
        cols.extend(name for _, name in FEATURE_COLUMNS)
    cols.extend(OPTIONAL_COLUMNS)
    return cols

UNIT_DISPLAY_BY_CODE = {
    "pcs": "Stück", "set": "Set", "pack": "Packung", "box": "Box", "m": "Meter",
    "cm": "cm", "mm": "mm", "kg": "kg", "g": "g", "l": "Liter", "ml": "ml",
}
UNIT_DROPDOWN_VALUES = list(UNIT_DISPLAY_BY_CODE.values())
UNIT_CODE_BY_NORMALIZED = {
    "pcs": "pcs", "stück": "pcs", "stueck": "pcs", "stk": "pcs",
    "set": "set", "pack": "pack", "packung": "pack", "box": "box",
    "m": "m", "meter": "m", "cm": "cm", "zentimeter": "cm",
    "mm": "mm", "millimeter": "mm", "kg": "kg", "kilogramm": "kg",
    "g": "g", "gramm": "g", "l": "l", "liter": "l", "ml": "ml", "milliliter": "ml",
}

HEADER_FILL = PatternFill("solid", fgColor="2C3E50")
HEADER_FONT = Font(bold=True, color="FFFFFF")
ODD_FILL = PatternFill("solid", fgColor="FFFFFF")
EVEN_FILL = PatternFill("solid", fgColor="F5F6FA")
THIN_BORDER = Border(
    left=Side(style="thin", color="DADCE0"), right=Side(style="thin", color="DADCE0"),
    top=Side(style="thin", color="DADCE0"), bottom=Side(style="thin", color="DADCE0"),
)

HEADER_ALIASES = {
    "name": "Name", "dashboard": "Dashboard", "overview": "Dashboard",
    "kategorie": "Kategorie", "category": "Kategorie", "ist-bestand": "Ist-Bestand",
    "bestand": "Ist-Bestand", "quantity": "Ist-Bestand", "einheit": "Einheit",
    "unit": "Einheit", "mindestbestand": "Mindestbestand", "min_stock": "Mindestbestand",
    "low_quantity": "Mindestbestand", "lagerort": "Lagerort", "storage_location": "Lagerort",
    "tags": "Tags", "bestell-link": "Bestell-Link", "order_link": "Bestell-Link",
    "variante": "Variante", "variant": "Variante", "wartungsdatum": "Wartungsdatum",
    "maintenance_date": "Wartungsdatum", "beschreibung": "Beschreibung", "description": "Beschreibung",
}


def generate_import_template(output_path, overview=None):
    """Generate an XLSX template with headers and data validation dropdowns."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Import"
    _setup_sheet(worksheet, overview)

    example_dashboard = Overview.objects.order_by("name").values_list("name", flat=True).first() or "Dashboard-Name"
    cols = get_columns_for_overview(overview)
    example_values = {
        "Name": "Beispielartikel",
        "Dashboard": example_dashboard,
        "Kategorie": "Werkzeug",
        "Ist-Bestand": 1,
        "Einheit": "Stück",
        "Tags": "Bohrer, Metall",
        "Bestell-Link": "https://example.com/bestellen",
        "Variante": "Standard",
        "Beschreibung": "Kurze Beschreibung des Artikels",
        "Mindestbestand": 3,
        "Lagerort": "Regal A > Fach 1",
        "Verleihbar": "–",
        "Bild-URL": "",
        "Notizen": "",
        "Wartungsdatum": date.today().isoformat(),
    }
    worksheet.append([example_values.get(c, "") for c in cols])

    _style_rows(worksheet, zebra=False)
    _add_validations(workbook, worksheet)
    _auto_width(worksheet)

    # Dashboard-Info-Blatt
    info = workbook.create_sheet("Dashboards")
    info_headers = ["Dashboard", "Typ", "Mindestbestand", "Verleih", "QR", "Lagerorte", "Kommentare", "Bilder", "Tags"]
    for col, h in enumerate(info_headers, 1):
        cell = info.cell(row=1, column=col, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
    for r, ov in enumerate(Overview.objects.filter(is_active=True).order_by("name"), 2):
        vals = [
            ov.name,
            "Verbrauchsmaterial" if ov.is_consumable_mode else "Equipment",
            "✓" if ov.has_min_stock else "–",
            "✓" if ov.enable_borrow else "–",
            "✓" if ov.require_qr else "–",
            "✓" if ov.has_locations else "–",
            "✓" if ov.enable_comments else "–",
            "✓" if ov.show_images else "–",
            "✓" if ov.show_tags else "–",
        ]
        for col, v in enumerate(vals, 1):
            cell = info.cell(row=r, column=col, value=v)
            cell.border = THIN_BORDER
    _auto_width(info)
    workbook.active = 0  # Zurück zum Import-Sheet

    _save_workbook(workbook, output_path)


def export_items_to_excel(output_path, overview=None):
    """Export all items (or filtered by overview) in the same format as the template."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Import"
    _setup_sheet(worksheet, overview)

    queryset = (
        InventoryItem.objects.select_related("overview", "category", "storage_location")
        .prefetch_related("application_tags")
        .order_by("overview__name", "name")
    )
    if overview is not None:
        queryset = queryset.filter(overview=overview)

    for item in queryset:
        worksheet.append(_item_to_row(item, overview))

    _style_rows(worksheet, zebra=True)
    _add_validations(workbook, worksheet)
    _auto_width(worksheet)
    _save_workbook(workbook, output_path)


def preview_import(file_path, overview=None):
    """Read Excel, return {rows: [...preview...], warnings: [...], errors: [...], total_valid: N}."""
    result = _parse_workbook(file_path, include_duplicate_warnings=True, overview=overview)
    preview_rows = []
    total_valid = 0

    for parsed in result["rows"]:
        status = "valid"
        if parsed["errors"]:
            status = "error"
        elif parsed["warnings"]:
            status = "warning"
        if not parsed["errors"]:
            total_valid += 1
        preview_rows.append({
            "row": parsed["row"], "status": status, "data": parsed["data"],
            "warnings": parsed["warnings"], "errors": parsed["errors"],
        })

    return {"rows": preview_rows, "warnings": result["warnings"], "errors": result["errors"], "total_valid": total_valid}


def execute_import(file_path, user, dry_run=False, override_overview=None, overview=None):
    """Actually import items. Returns {imported: N, skipped: N, errors: [...]}"""
    parsed = _parse_workbook(file_path, include_duplicate_warnings=False, overview=overview)
    imported = 0
    skipped = 0
    # _parse_workbook returns row-level errors both globally and on each row for
    # previews. For execution, report row errors once while still preserving
    # workbook-level errors such as missing headers.
    errors = list(parsed["errors"]) if not parsed["rows"] else []

    for row in parsed["rows"]:
        if row["errors"]:
            skipped += 1
            for message in row["errors"]:
                errors.append({"row": row["row"], "message": message})
            continue

        data = row["parsed"]
        try:
            if not dry_run:
                with transaction.atomic():
                    category = None
                    if data["category_name"]:
                        category = data["category"] or Category.objects.create(name=data["category_name"])

                    overview = override_overview if override_overview else data["overview"]
                    item = InventoryItem.objects.create(
                        name=data["name"], overview=overview, category=category,
                        quantity=data["quantity"], unit=data["unit"], low_quantity=data["low_quantity"],
                        storage_location=data["storage_location"], order_link=data["order_link"] or None,
                        variant=data["variant"], maintenance_date=data["maintenance_date"],
                        description=data["description"] or "", user=user,
                    )
                    tags = [_get_or_create_tag(name) for name in data["tag_names"]]
                    if tags:
                        item.application_tags.set(tags)
            imported += 1
        except Exception as exc:  # pragma: no cover - defensive result reporting for callers
            skipped += 1
            errors.append({"row": row["row"], "message": str(exc)})

    return {"imported": imported, "skipped": skipped, "errors": errors}


def _setup_sheet(worksheet, overview=None):
    cols = get_columns_for_overview(overview)
    worksheet.append(cols)
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{get_column_letter(len(cols))}1"


def _style_rows(worksheet, zebra: bool):
    for row_idx, row in enumerate(worksheet.iter_rows(), start=1):
        fill = HEADER_FILL if row_idx == 1 else (EVEN_FILL if zebra and row_idx % 2 == 0 else ODD_FILL)
        for cell in row:
            cell.border = THIN_BORDER
            cell.fill = fill
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if row_idx == 1:
                cell.font = HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")


def _add_validations(workbook, worksheet):
    unit_validation = DataValidation(
        type="list", formula1='"{}"'.format(",".join(UNIT_DROPDOWN_VALUES)), allow_blank=True,
    )
    unit_validation.error = "Bitte eine gültige Einheit auswählen."
    unit_validation.errorTitle = "Ungültige Einheit"
    worksheet.add_data_validation(unit_validation)
    unit_validation.add("E2:E1048576")

    overview_names = list(Overview.objects.order_by("name").values_list("name", flat=True))
    if overview_names:
        hidden = workbook.create_sheet("_dropdowns")
        hidden.sheet_state = "hidden"
        for row_idx, name in enumerate(overview_names, start=1):
            hidden.cell(row=row_idx, column=1, value=name)
        formula = f"={quote_sheetname(hidden.title)}!$A$1:$A${len(overview_names)}"
        dashboard_validation = DataValidation(type="list", formula1=formula, allow_blank=False)
    else:
        dashboard_validation = DataValidation(type="list", formula1='""', allow_blank=True)
    dashboard_validation.error = "Bitte ein vorhandenes Dashboard auswählen."
    dashboard_validation.errorTitle = "Ungültiges Dashboard"
    worksheet.add_data_validation(dashboard_validation)
    dashboard_validation.add("B2:B1048576")


def _auto_width(worksheet):
    for col_idx, column_cells in enumerate(worksheet.columns, start=1):
        max_length = 0
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        worksheet.column_dimensions[get_column_letter(col_idx)].width = min(max(max_length + 2, 12), 50)


def _save_workbook(workbook, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)


def _item_to_row(item: InventoryItem, overview=None):
    cols = get_columns_for_overview(overview or item.overview)
    col_map = {
        "Name": item.name,
        "Dashboard": item.overview.name if item.overview else "",
        "Kategorie": item.category.name if item.category else "",
        "Ist-Bestand": item.quantity,
        "Einheit": UNIT_DISPLAY_BY_CODE.get(item.unit, item.get_unit_display() if item.unit else ""),
        "Tags": ", ".join(sorted(item.application_tags.values_list("name", flat=True))),
        "Bestell-Link": item.order_link or "",
        "Variante": item.variant or "",
        "Beschreibung": item.description or "",
        "Mindestbestand": item.low_quantity,
        "Lagerort": item.storage_location.get_full_path() if item.storage_location else "",
        "Verleihbar": "✓" if item.is_active else "–",
        "Bild-URL": item.image.url if item.image else "",
        "Notizen": "",
        "Wartungsdatum": item.maintenance_date.isoformat() if item.maintenance_date else "",
    }
    return [col_map.get(c, "") for c in cols]


def _parse_workbook(file_path, include_duplicate_warnings: bool, overview=None):
    workbook = load_workbook(file_path, data_only=True)
    worksheet = workbook.active
    header_map = _header_map(worksheet)
    rows = []
    warnings = []
    errors = []

    cols = get_columns_for_overview(overview)
    missing_headers = [header for header in cols if header not in header_map]
    if missing_headers:
        errors.append({"row": 1, "message": f"Fehlende Spalten: {', '.join(missing_headers)}"})
        return {"rows": rows, "warnings": warnings, "errors": errors}

    for row_idx in range(2, worksheet.max_row + 1):
        raw = {header: _cell_value(worksheet.cell(row=row_idx, column=header_map[header])) for header in cols if header in header_map}
        if not any(value not in (None, "") for value in raw.values()):
            continue

        parsed, row_warnings, row_errors = _validate_row(raw)
        if parsed.get("name") and include_duplicate_warnings:
            duplicates = find_similar_items(parsed["name"])
            if duplicates:
                row_warnings.append(
                    "Mögliche Duplikate gefunden: "
                    + ", ".join(f"{entry['name']} (#{entry['id']})" for entry in duplicates[:5])
                )

        data = {
            "name": parsed.get("name") or _string(raw["Name"]),
            "dashboard": _string(raw["Dashboard"]),
            "kategorie": _string(raw["Kategorie"]),
            "ist_bestand": raw["Ist-Bestand"],
            "einheit": _string(raw["Einheit"]),
            "mindestbestand": raw["Mindestbestand"],
            "lagerort": _string(raw["Lagerort"]),
            "tags": _string(raw["Tags"]),
            "bestell_link": _string(raw["Bestell-Link"]),
            "variante": _string(raw["Variante"]),
            "wartungsdatum": _format_date_for_preview(parsed.get("maintenance_date"), raw["Wartungsdatum"]),
            "beschreibung": _string(raw["Beschreibung"]),
        }

        for message in row_warnings:
            warnings.append({"row": row_idx, "message": message})
        for message in row_errors:
            errors.append({"row": row_idx, "message": message})

        rows.append({"row": row_idx, "data": data, "parsed": parsed, "warnings": row_warnings, "errors": row_errors})

    return {"rows": rows, "warnings": warnings, "errors": errors}


def _header_map(worksheet):
    header_map = {}
    for cell in worksheet[1]:
        key = _normalise(cell.value)
        canonical = HEADER_ALIASES.get(key)
        if canonical and canonical not in header_map:
            header_map[canonical] = cell.column
    return header_map


def _validate_row(raw: dict[str, Any]):
    warnings = []
    errors = []

    name = _string(raw["Name"])
    if not name:
        errors.append("Name ist erforderlich.")

    overview_name = _string(raw["Dashboard"])
    overview = _match_by_name(Overview, overview_name)
    if not overview:
        errors.append(f"Dashboard '{overview_name or '–'}' existiert nicht.")

    category_name = _string(raw["Kategorie"])
    category = _match_by_name(Category, category_name) if category_name else None
    if category_name and not category:
        warnings.append(f"Kategorie '{category_name}' wurde nicht gefunden und wird beim Import angelegt.")

    storage_location_name = _string(raw["Lagerort"])
    storage_location = _match_storage_location(storage_location_name) if storage_location_name else None
    if storage_location_name and not storage_location:
        warnings.append(f"Lagerort '{storage_location_name}' wurde nicht gefunden; das Item wird ohne Lagerort importiert.")

    quantity = _parse_int(raw["Ist-Bestand"], default=0, field_name="Ist-Bestand", errors=errors)
    low_quantity = _parse_int(raw["Mindestbestand"], default=3, field_name="Mindestbestand", errors=errors)
    unit = _parse_unit(raw["Einheit"], errors)
    maintenance_date = _parse_date(raw["Wartungsdatum"], errors)
    tag_names = _split_names(raw["Tags"])

    return {
        "name": name, "overview_name": overview_name, "overview": overview,
        "category_name": category_name, "category": category, "quantity": quantity,
        "unit": unit, "low_quantity": low_quantity, "storage_location_name": storage_location_name,
        "storage_location": storage_location, "tag_names": tag_names,
        "order_link": _string(raw["Bestell-Link"]), "variant": _string(raw["Variante"]),
        "maintenance_date": maintenance_date, "description": _string(raw["Beschreibung"]),
    }, warnings, errors


def _match_by_name(model, value: str):
    if not value:
        return None
    return model.objects.filter(name__iexact=value.strip()).first()


def _match_storage_location(value: str):
    needle = _normalise_path(value)
    if not needle:
        return None
    locations = StorageLocation.objects.select_related("parent", "parent__parent", "parent__parent__parent").all()
    for location in locations:
        if _normalise_path(location.get_full_path()) == needle:
            return location
    return None


def _parse_int(value, default: int, field_name: str, errors: list[str]):
    if value in (None, ""):
        return default
    try:
        decimal = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        errors.append(f"{field_name} muss eine Zahl sein.")
        return default
    if decimal != decimal.to_integral_value():
        errors.append(f"{field_name} muss eine ganze Zahl sein.")
        return default
    return int(decimal)


def _parse_unit(value, errors: list[str]):
    raw = _string(value)
    if not raw:
        return "pcs"
    code = UNIT_CODE_BY_NORMALIZED.get(_normalise(raw))
    if code:
        return code
    valid = ", ".join(UNIT_DROPDOWN_VALUES)
    errors.append(f"Einheit '{raw}' ist ungültig. Gültige Werte: {valid}.")
    return "pcs"


def _parse_date(value, errors: list[str]):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _string(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    errors.append(f"Wartungsdatum '{raw}' ist ungültig. Erwartet wird YYYY-MM-DD.")
    return None


def _split_names(value):
    return [part.strip() for part in _string(value).split(",") if part.strip()]


def _get_or_create_tag(name: str):
    existing = ApplicationTag.objects.filter(name__iexact=name).first()
    if existing:
        return existing
    return ApplicationTag.objects.create(name=name)


def _cell_value(cell):
    value = cell.value
    if isinstance(value, str):
        return value.strip()
    return value


def _string(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalise(value) -> str:
    return _string(value).casefold().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe").replace("ß", "ss")


def _normalise_path(value) -> str:
    return " > ".join(part.strip() for part in _normalise(value).replace("/", ">").split(">") if part.strip())


def _format_date_for_preview(parsed_date, raw):
    if parsed_date:
        return parsed_date.isoformat()
    return _string(raw)
