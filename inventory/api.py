# inventory/api.py
from __future__ import annotations

import os
from typing import Any, Dict

from django.conf import settings
from django.views import View
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now

from .models import Feedback
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
