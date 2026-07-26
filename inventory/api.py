# inventory/api.py
from __future__ import annotations

import os
from typing import Any, Dict

from django.conf import settings
from django.views import View
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now

from .models import Feedback, ItemMark, Category, ApplicationTag, TagType, Overview, StorageLocation
from .admin_views import _get_tailscale_status, _get_global_settings
from .integrations.homeassistant import check_available, get_status_tuple, get_diagnostics

API_KEY = os.getenv("FEEDBACK_API_KEY", "").strip()  # optionaler Schutz (?key=...)


def _is_local(request) -> bool:
    if settings.DEBUG:
        return True
    ra = request.META.get("REMOTE_ADDR", "")
    return ra in ("127.0.0.1", "::1")


def _require_key(request):
    if not API_KEY:
        return None
    if _is_local(request):
        return None
    if request.GET.get("key") == API_KEY:
        return None
    return HttpResponseForbidden("invalid key")


class FeedbackSummaryAPI(View):
    def get(self, request):
        guard = _require_key(request)
        if guard is not None:
            return guard

        qs = Feedback.objects.select_related("created_by").order_by("-created_at")
        data: Dict[str, Any] = {
            "open": qs.filter(status=Feedback.Status.OFFEN).count(),
            "in_progress": qs.filter(status=Feedback.Status.IN_ARBEIT).count(),
            "done": qs.filter(status=Feedback.Status.ERLEDIGT).count(),
            "last": [
                {
                    "id": fb.id,
                    "title": fb.title,
                    "status": fb.status,
                    "status_display": fb.get_status_display(),
                    "created_by": fb.created_by.username if fb.created_by_id else None,
                    "created_at": localtime(fb.created_at).strftime("%Y-%m-%d %H:%M"),
                }
                for fb in qs[:5]
            ],
        }
        return JsonResponse(data, json_dumps_params={"ensure_ascii": False})


class HAStatusAPI(View):
    def get(self, request):
        guard = _require_key(request)
        if guard is not None:
            return guard

        force = request.GET.get("force") in ("1", "true", "True", "yes")
        available = check_available(force=force)
        ok, message = get_status_tuple()

        payload = {
            "available": bool(available and ok),
            "message": message,
            "checked_at": now().isoformat(),
        }

        # Debug-Infos nur wenn explizit angefragt oder DEBUG True
        if request.GET.get("debug") in ("1", "true", "True") or settings.DEBUG:
            diag = get_diagnostics()
            # Token niemals rausgeben
            diag.pop("has_token", None)  # bool wäre ok, aber wir lassen's weg, um Verwirrung zu vermeiden
            payload["diagnostics"] = diag

        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


class SystemHealthAPI(View):
    def get(self, request):
        guard = _require_key(request)
        if guard is not None:
            return guard

        settings_obj = _get_global_settings()
        tailscale_status = _get_tailscale_status()

        try:
            from django.db import connection

            connection.ensure_connection()
            db_status = "ok"
        except Exception:
            db_status = "error"

        disk_total = disk_free = None
        try:
            import shutil

            disk = shutil.disk_usage(settings.BASE_DIR)
            disk_total = disk.total
            disk_free = disk.free
        except OSError:
            pass

        payload = {
            "db_status": db_status,
            "maintenance_mode": settings_obj.maintenance_mode_enabled,
            "last_backup_at": settings_obj.last_backup_at.isoformat() if settings_obj.last_backup_at else None,
            "backup_interval_days": settings_obj.backup_interval_days,
            "backup_retention_count": settings_obj.backup_retention_count,
            "backup_storage_path": settings_obj.backup_storage_path,
            "tailscale": {
                "connected": tailscale_status.get("connected"),
                "hostname": tailscale_status.get("hostname"),
                "dns_name": tailscale_status.get("dns_name"),
                "ips": tailscale_status.get("ips"),
                "error": tailscale_status.get("error"),
            },
            "disk": {
                "total_bytes": disk_total,
                "free_bytes": disk_free,
            },
            "checked_at": now().isoformat(),
        }

        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


class MarkedItemsAPI(View):
    """
    REST-API für den ESP32 (LED-Anzeige).
    Gibt alle aktuell markierten Items mit dem **untersten StorageLocation**
    (Blattknoten im Lagerort-Baum) zurück. Die LED-Position ergibt sich aus
    der `location_id` (1:1-Mapping: location_id → LED-Index).

    Aufruf:
        GET /api/marked-items/?key=DEIN_KEY

    Antwort:
        {
            "marks": [
                {
                    "id": 42,
                    "name": "Schraube M8",
                    "location_id": 7,
                    "location_name": "Schublade 1",
                    "location_path": "Regal A > Schublade 1",
                    "mark_id": 1,
                    "marked_at": "2026-06-26T07:09:00+00:00",
                    "is_active": true
                }
            ],
            "count": 1,
            "checked_at": "2026-06-26T07:09:03+00:00"
        }
    """
    def get(self, request):
        guard = _require_key(request)
        if guard is not None:
            return guard
        # Automatisch abgelaufene Markierungen löschen (ESP-Auto-Clear)
        from django.utils.timezone import now as dj_now
        from datetime import timedelta
        import logging
        logger = logging.getLogger(__name__)
        from .models import GlobalSettings

        gs = GlobalSettings.objects.first() or GlobalSettings.objects.create()
        if gs.esp_mark_auto_clear_seconds > 0:
            cutoff = dj_now() - timedelta(seconds=gs.esp_mark_auto_clear_seconds)
            expired = ItemMark.objects.filter(
                cleared_at__isnull=True,
                marked_at__lt=cutoff
            )
            ec = expired.count()
            if ec:
                expired.update(cleared_at=dj_now())
                logger.info(f"ESP-Auto-Clear: {ec} Markierung(en) aufgehoben")


        if not request.GET.get("all"):
            marks = ItemMark.objects.filter(
                cleared_at__isnull=True
            ).select_related("item", "location").order_by("-marked_at")
        else:
            marks = ItemMark.objects.select_related("item", "location").order_by("-marked_at")[:50]

        data = []
        now_ts = now()
        for mark in marks:
            loc = mark.location
            entry = {
                "id": mark.item.id,
                "name": mark.item.name,
                "location_id": loc.id if loc else None,
                "location_name": loc.name if loc else "?",
                "location_path": loc.get_full_path() if loc else "?",
                "mark_id": mark.id,
                "marked_at": mark.marked_at.isoformat(),
                "is_active": mark.is_active,
            }
            data.append(entry)

        return JsonResponse({
            "marks": data,
            "count": len(data),
            "checked_at": now_ts.isoformat(),
        }, json_dumps_params={"ensure_ascii": False})


# ---------------------------------------------------------------------------
# Quick-Add API: Neue Kategorie / neuer Tag direkt aus dem Item-Formular
# ---------------------------------------------------------------------------

class QuickAddCategoryAPI(View):
    """
    POST /api/categories/quick-add/
    Body: { "name": "Elektronik" }
    Response (Admin):  { "success": true, "id": 42, "name": "Elektronik", "status": "created" }
    Response (User):   { "success": true, "id": null, "name": "Elektronik", "status": "requested" }
    """

    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Ungültiges JSON"}, status=400)

        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "Name ist erforderlich"}, status=400)

        if Category.objects.filter(name__iexact=name).exists():
            existing = Category.objects.get(name__iexact=name)
            return JsonResponse({
                "success": True,
                "id": existing.id,
                "name": existing.name,
                "status": "exists",
            })

        if request.user.is_superuser:
            cat = Category.objects.create(name=name)
            return JsonResponse({
                "success": True,
                "id": cat.id,
                "name": cat.name,
                "status": "created",
            })
        else:
            # PendingRequest für normale User
            from .models import PendingCategoryRequest
            PendingCategoryRequest.objects.create(
                name=name,
                requested_by=request.user,
            )
            return JsonResponse({
                "success": True,
                "id": None,
                "name": name,
                "status": "requested",
                "message": "Deine Anfrage wurde an den Admin weitergeleitet.",
            })


class QuickAddTagAPI(View):
    """
    POST /api/tags/quick-add/
    Body: { "name": "Sensor", "type_name": "Equipment" }
    Response (Admin):  { "success": true, "id": 7, "name": "Sensor", "status": "created" }
    Response (User):   { "success": true, "id": null, "name": "Sensor", "status": "requested" }
    """

    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Ungültiges JSON"}, status=400)

        name = data.get("name", "").strip()
        type_name = data.get("type_name", "").strip()

        if not name:
            return JsonResponse({"success": False, "error": "Name ist erforderlich"}, status=400)

        if ApplicationTag.objects.filter(name__iexact=name).exists():
            existing = ApplicationTag.objects.get(name__iexact=name)
            return JsonResponse({
                "success": True,
                "id": existing.id,
                "name": existing.name,
                "status": "exists",
            })

        tag_type = None
        if type_name:
            try:
                tag_type = TagType.objects.get(name=type_name)
            except TagType.DoesNotExist:
                pass

        if request.user.is_superuser:
            tag = ApplicationTag.objects.create(name=name, type=tag_type)
            return JsonResponse({
                "success": True,
                "id": tag.id,
                "name": tag.name,
                "status": "created",
            })
        else:
            # PendingRequest für normale User
            from .models import PendingTagRequest
            PendingTagRequest.objects.create(
                name=name,
                type_name=type_name,
                requested_by=request.user,
            )
            return JsonResponse({
                "success": True,
                "id": None,
                "name": name,
                "status": "requested",
                "message": "Deine Anfrage wurde an den Admin weitergeleitet.",
            })


class QuickAddStorageLocationAPI(View):
    """
    POST /api/storage-locations/quick-add/
    Body: { "name": "Regal A" }
    Response: { "success": true, "id": 42, "name": "Regal A", "status": "created" }
    """

    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Ungültiges JSON"}, status=400)

        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "Name ist erforderlich"}, status=400)

        existing = StorageLocation.objects.filter(name__iexact=name, parent__isnull=True).first()
        if existing:
            return JsonResponse({
                "success": True,
                "id": existing.id,
                "name": existing.get_full_path(),
                "status": "exists",
            })

        location = StorageLocation.objects.create(name=name)
        return JsonResponse({
            "success": True,
            "id": location.id,
            "name": location.get_full_path(),
            "status": "created",
        })
