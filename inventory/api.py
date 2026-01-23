# inventory/api.py
from __future__ import annotations

import os
from typing import Any, Dict

from django.conf import settings
from django.views import View
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now

from .models import Feedback
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
