"""
Thread-lokale Hilfsfunktionen für Request-Kontext und GlobalSettings-Caching.

Vereinigt die früheren Dateien middleware.py und utils.py,
um doppelte threading.local-Nutzung zu vermeiden.
"""
from __future__ import annotations

import threading
from typing import Optional

from django.http import HttpRequest
from django.shortcuts import render


# ---------------------------------------------------------------------------
# Thread-lokaler Speicher für die aktuelle Request
# ---------------------------------------------------------------------------
_request_local = threading.local()


def get_current_request() -> Optional[HttpRequest]:
    """Gibt die aktuelle HttpRequest zurück, falls von der Middleware gesetzt, sonst None."""
    return getattr(_request_local, "request", None)


class ThreadLocalMiddleware:
    """
    Speichert für die Dauer der Anfrage die HttpRequest in einem Thread-Local.
    Diese Middleware muss in settings.MIDDLEWARE eingetragen sein (nach AuthenticationMiddleware).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        _request_local.request = request
        try:
            response = self.get_response(request)
        finally:
            _request_local.request = None
        return response


# ---------------------------------------------------------------------------
# GlobalSettings-Caching (pro Request per Thread)
# ---------------------------------------------------------------------------
_gs_threadlocal = threading.local()


def get_global_settings():
    """
    Gibt GlobalSettings-Instanz zurück – mit Thread-Caching pro Request.

    Der Cache wird beim ersten Aufruf innerhalb eines Request-Threads befüllt
    und gilt bis zum Ende des Requests. So wird GlobalSettings.objects.first()
    nicht mehrfach pro Request aus der DB geladen.

    Der Cache wird über den request_started-Hook zurückgesetzt (siehe apps.py).
    """
    from .models import GlobalSettings

    if not hasattr(_gs_threadlocal, "global_settings_cached"):
        _gs_threadlocal.global_settings_cached = True
        _gs_threadlocal.global_settings = GlobalSettings.objects.first()
    return _gs_threadlocal.global_settings


def clear_global_settings_cache():
    """Setzt den GlobalSettings-Cache zurück – wird bei jedem Request-Start aufgerufen."""
    if hasattr(_gs_threadlocal, "global_settings_cached"):
        del _gs_threadlocal.global_settings_cached
    if hasattr(_gs_threadlocal, "global_settings"):
        del _gs_threadlocal.global_settings


# ---------------------------------------------------------------------------
# Maintenance Mode Middleware
# ---------------------------------------------------------------------------
class MaintenanceModeMiddleware:
    """
    Zeigt eine Wartungsseite an, wenn maintenance_mode_enabled aktiv ist.
    Superuser und Staff dürfen weiterhin alles nutzen.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.path in {"/login/", "/logout/"}:
            return self.get_response(request)

        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return self.get_response(request)

        settings_obj = get_global_settings()
        if settings_obj and settings_obj.maintenance_mode_enabled:
            context = {"message": settings_obj.maintenance_message}
            return render(request, "inventory/maintenance.html", context, status=503)

        return self.get_response(request)


__all__ = [
    "get_current_request",
    "ThreadLocalMiddleware",
    "MaintenanceModeMiddleware",
    "get_global_settings",
    "clear_global_settings_cache",
]
