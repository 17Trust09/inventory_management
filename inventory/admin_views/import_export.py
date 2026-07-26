"""Admin import/export UI for inventory data."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from ..import_export import (
    export_items_to_excel,
    execute_import,
    generate_import_template,
    preview_import,
)
from ..models import Overview
from .helpers import staff_required


def _template_response(overview=None):
    with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        generate_import_template(tmp.name, overview=overview)
        tmp.seek(0)
        data = tmp.read()
    response = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="inventar_import_vorlage.xlsx"'
    return response


def _export_backup_response(overview_id: str | None = None):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    if overview_id:
        from django.shortcuts import get_object_or_404
        overview = get_object_or_404(Overview, pk=overview_id, is_active=True)
        with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            export_items_to_excel(tmp.name, overview=overview)
            tmp.seek(0)
            data = tmp.read()
        return HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           headers={"Content-Disposition": f'attachment; filename="backup_{overview.slug}_{timestamp}.xlsx"'})

    overviews = list(Overview.objects.filter(is_active=True).order_by("order", "name"))
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
        for ov in overviews:
            with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                export_items_to_excel(tmp.name, overview=ov)
                zip_file.write(tmp.name, arcname=f"{ov.slug}_{timestamp}.xlsx")
    archive.seek(0)
    response = HttpResponse(archive.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="backup_alle_dashboards_{timestamp}.zip"'
    return response


@staff_required
def admin_import_export(request):
    """Main import/export page using the backend import_export helpers."""
    import_result = request.session.pop("admin_import_result", None)
    preview = None

    if request.method == "POST":
        action = request.POST.get("action")

        if request.POST.get("download_template") or action == "download_template":
            overview_id = request.POST.get("overview_id")
            overview = None
            if overview_id:
                overview = Overview.objects.filter(pk=overview_id, is_active=True).first()
            return _template_response(overview)

        if action == "export_backup":
            overview_id = request.POST.get("overview_id") or None
            return _export_backup_response(overview_id)

        if action == "preview":
            upload = request.FILES.get("import_file")
            if not upload:
                messages.error(request, "Bitte eine Excel-Datei auswählen.")
                return redirect("admin_import_export")
            if not upload.name.lower().endswith(".xlsx"):
                messages.error(request, "Bitte eine .xlsx-Datei hochladen.")
                return redirect("admin_import_export")
            saved_path = default_storage.save(
                f"imports/admin_import_{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx", upload
            )
            request.session["admin_import_file"] = saved_path
            full_path = Path(settings.MEDIA_ROOT) / saved_path
            overview_id = request.POST.get("overview_id")
            overview = Overview.objects.filter(pk=overview_id, is_active=True).first() if overview_id else None
            preview = preview_import(str(full_path), overview=overview)
            preview["counts"] = {
                "valid": preview["total_valid"],
                "warning": sum(1 for r in preview["rows"] if r["status"] == "warning"),
                "error": sum(1 for r in preview["rows"] if r["status"] == "error"),
            }

        elif action == "execute":
            saved_path = request.session.get("admin_import_file")
            if not saved_path or not default_storage.exists(saved_path):
                messages.error(request, "Keine vorbereitete Importdatei gefunden. Bitte Datei erneut hochladen.")
                return redirect("admin_import_export")
            full_path = str(Path(settings.MEDIA_ROOT) / saved_path)
            overview_id = request.POST.get("overview_id")
            overview = None
            if overview_id:
                overview = Overview.objects.filter(pk=overview_id, is_active=True).first()
            if not overview:
                messages.error(request, "Bitte ein gültiges Dashboard auswählen.")
                return redirect("admin_import_export")
            import_result = execute_import(full_path, request.user, dry_run=False, override_overview=overview)
            request.session.pop("admin_import_file", None)
            try:
                default_storage.delete(saved_path)
            except Exception:
                pass
            request.session["admin_import_result"] = import_result
            msg = f"Import abgeschlossen: {import_result['imported']} importiert, {import_result['skipped']} übersprungen."
            if import_result.get("errors"):
                msg += f" ({len(import_result['errors'])} Fehler)"
            messages.success(request, msg)
            return redirect("admin_import_export")

    overviews = Overview.objects.filter(is_active=True).order_by("order", "name")
    return render(request, "inventory/admin_import_export.html", {
        "overviews": overviews,
        "import_result": import_result,
        "preview": preview,
    })
