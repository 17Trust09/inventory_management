# inventory/middleware.py
from __future__ import annotations

import threading
from typing import Optional
from django.http import HttpRequest

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
