"""
Hilfsfunktionen für inventory_management.
"""

import threading
from .models import GlobalSettings

_thread_locals = threading.local()


def get_global_settings():
    """
    Gibt GlobalSettings-Instanz zurück – mit Thread-Caching pro Request.

    Der Cache wird beim ersten Aufruf innerhalb eines Request-Threads befüllt
    und gilt bis zum Ende des Requests. So wird GlobalSettings.objects.first()
    nicht mehrfach pro Request aus der DB geladen.

    Der Cache wird automatisch über den request_started-Hook zurückgesetzt,
    der in apps.py registriert ist.
    """
    if not hasattr(_thread_locals, "global_settings_cached"):
        _thread_locals.global_settings_cached = True
        _thread_locals.global_settings = GlobalSettings.objects.first()
    return _thread_locals.global_settings


def clear_global_settings_cache():
    """Setzt den Cache zurück – wird bei jedem Request-Start aufgerufen."""
    if hasattr(_thread_locals, "global_settings_cached"):
        del _thread_locals.global_settings_cached
    if hasattr(_thread_locals, "global_settings"):
        del _thread_locals.global_settings
