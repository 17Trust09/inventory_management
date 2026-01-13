# inventory/api.py
from __future__ import annotations

from typing import Any, Dict

from django.conf import settings
from django.views import View
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now

from .models import Feedback
from .integrations.homeassistant import check_available, get_status_tuple, get_diagnostics


def _is_local(request) -> bool:
    ra = request.META.get("REMOTE_ADDR", "")
    return ra in ("127.0.0.1", "::1")


def _is_key_valid(request) -> bool:
    api_key = settings.FEEDBACK_API_KEY.strip()
    if not api_key:
        return False
    return request.GET.get("key") == api_key


def _require_key(request):
    api_key = settings.FEEDBACK_API_KEY.strip()
    if not api_key:
        if settings.DEBUG:
            return None
        return HttpResponseForbidden("missing key")
    if _is_key_valid(request):
        return None
    return HttpResponseForbidden("invalid key")


def _can_view_diagnostics(request) -> bool:
    if _is_key_valid(request):
        return True
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


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

        # Debug-Infos nur wenn explizit angefragt und autorisiert
        if request.GET.get("debug") in ("1", "true", "True") and _can_view_diagnostics(request):
            diag = get_diagnostics()
            # Token niemals rausgeben
            diag.pop("has_token", None)  # bool wäre ok, aber wir lassen's weg, um Verwirrung zu vermeiden
            payload["diagnostics"] = diag

        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
