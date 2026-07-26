from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable, Sequence

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .exports import get_export_columns


def _pdf_safe(value) -> str:
    """Return text that ReportLab's built-in Helvetica/WinAnsi font can render."""
    if value is None:
        return ""
    text = str(value)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _image_cell(item, max_width: float = 26 * mm, max_height: float = 20 * mm):
    image_field = getattr(item, "image", None)
    if not image_field:
        return ""

    image_path = getattr(image_field, "path", None)
    if not image_path or not os.path.exists(image_path):
        return ""

    try:
        with PILImage.open(image_path) as img:
            width, height = img.size
    except Exception:
        return ""

    if not width or not height:
        return ""

    scale = min(max_width / width, max_height / height, 1.0)
    return RLImage(image_path, width=width * scale, height=height * scale)


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6c757d"))
    y = 9 * mm
    canvas.drawString(doc.leftMargin, y, "Erstellt mit Icekey Inventory")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Seite {doc.page}")
    canvas.restoreState()


def _column_widths(columns: Sequence[tuple], available_width: float) -> list[float]:
    image_width = 28 * mm
    image_cols = sum(1 for key, _label, _getter in columns if key == "image")
    fixed = image_cols * image_width
    text_cols = max(len(columns) - image_cols, 1)
    text_width = max((available_width - fixed) / text_cols, 8 * mm)
    widths = []
    for key, _label, _getter in columns:
        widths.append(image_width if key == "image" else text_width)
    return widths


def export_overview_to_pdf(overview, columns: Iterable[str] | Iterable[tuple] | None, output_path):
    """Generate a styled PDF with items including images."""
    selected_columns = list(columns or [])
    if selected_columns and isinstance(selected_columns[0], tuple):
        export_columns = selected_columns
    else:
        export_columns = get_export_columns(selected_columns or None)

    if not export_columns:
        export_columns = get_export_columns(None)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title=f"Icekey Inventory - {_pdf_safe(getattr(overview, 'name', 'Dashboard'))}",
        author="Icekey Inventory",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "IcekeyTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1f2d3d"),
        spaceAfter=3 * mm,
    )
    subtitle_style = ParagraphStyle(
        "IcekeySubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#4f5b66"),
        spaceAfter=8 * mm,
    )
    header_style = ParagraphStyle(
        "IcekeyTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    cell_style = ParagraphStyle(
        "IcekeyTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#222222"),
    )
    right_cell_style = ParagraphStyle(
        "IcekeyTableCellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    items = list(
        overview.items.select_related("category", "storage_location", "overview")
        .prefetch_related("application_tags")
        .order_by("name")
    )

    icon = _pdf_safe(getattr(overview, "icon_emoji", "") or "")
    dashboard_name = _pdf_safe(getattr(overview, "name", "Dashboard"))
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    story = [
        Paragraph("Icekey", title_style),
        Paragraph(
            f"Dashboard: {icon} {dashboard_name} | {generated_at} | {len(items)} Artikel",
            subtitle_style,
        ),
        Spacer(1, 2 * mm),
    ]

    header = [Paragraph(_pdf_safe(label), header_style) for _key, label, _getter in export_columns]
    data = [header]

    numeric_keys = {"id", "quantity", "min_stock", "location_number"}
    for item in items:
        row = []
        for key, _label, getter in export_columns:
            if key == "image":
                row.append(_image_cell(item))
            else:
                try:
                    value = getter(item)
                except Exception:
                    value = ""
                style = right_cell_style if key in numeric_keys else cell_style
                row.append(Paragraph(_pdf_safe(value), style))
        data.append(row)

    available_width = doc.pagesize[0] - doc.leftMargin - doc.rightMargin
    table = Table(
        data,
        colWidths=_column_widths(export_columns, available_width),
        repeatRows=1,
        hAlign="LEFT",
    )

    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d7dce1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
    for row_index in range(1, len(data)):
        bg = colors.white if row_index % 2 else colors.HexColor("#f0f0f0")
        table_style.add("BACKGROUND", (0, row_index), (-1, row_index), bg)
    for col_index, (key, _label, _getter) in enumerate(export_columns):
        if key in numeric_keys:
            table_style.add("ALIGN", (col_index, 1), (col_index, -1), "RIGHT")
        if key == "image":
            table_style.add("ALIGN", (col_index, 1), (col_index, -1), "CENTER")
    table.setStyle(table_style)
    story.append(table)

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
