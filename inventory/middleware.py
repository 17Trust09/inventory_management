# inventory/middleware.py
from __future__ import annotations

import threading
from typing import Optional
from django.http import HttpRequest
from django.shortcuts import render

# Thread-lokaler Speicher für die aktuelle Request
_request_local = threading.local()


def get_current_request() -> Optional[HttpRequest]:
    """Gibt die aktuelle HttpRequest zurück, falls von der Middleware gesetzt, sonst None."""
    return getattr(_request_local, "request", None)


class ThreadLocalMiddleware:
    """
    Speichert für die Dauer der Anfrage die HttpRequest in einem Thread-Local.
    Diese Middleware muss in settings.MIDDLEWARE eingetragen werden (nach AuthenticationMiddleware ist gut).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        _request_local.request = request
        try:
            response = self.get_response(request)
        finally:
            # nach der Antwort wieder aufräumen
            _request_local.request = None
        return response


class MaintenanceModeMiddleware:
    """
    Zeigt eine Wartungsseite an, wenn maintenance_mode_enabled aktiv ist.
    Superuser und Staff dürfen weiterhin alles nutzen.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        from .models import GlobalSettings  # Lokaler Import, um App-Loading sauber zu halten.

        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return self.get_response(request)

        settings_obj = GlobalSettings.objects.first()
        if settings_obj and settings_obj.maintenance_mode_enabled:
            context = {"message": settings_obj.maintenance_message}
            return render(request, "inventory/maintenance.html", context, status=503)

        return self.get_response(request)
