import os
from .feature_flags import get_feature_flags_namespace
from .threadlocal import get_global_settings
from .models import Overview


def active_overviews(request):
    """
    Liefert alle aktiven Overviews in jedem Template-Kontext,
    falls global benötigt (z. B. für eine Sidebar).
    """
    ctx = {"active_overviews": Overview.objects.filter(is_active=True)}

    # URL-Name für aktive Navigations-Hervorhebung
    url_name = ""
    if request.resolver_match:
        url_name = request.resolver_match.url_name or ""
    ctx["active_nav"] = url_name

    return ctx


def app_version(request):
    try:
        with open(os.path.join(settings.BASE_DIR, 'VERSION')) as f:
            version = f.read().strip()
    except Exception:
        version = '2.0.0'
    return {'APP_VERSION': version}


def global_features(request):
    """
    Liefert globale Feature-Schalter für Templates.
    """
    return {"global_features": get_feature_flags_namespace()}


def maintenance_status(request):
    """
    Liefert Wartungsmodus-Status und Nachricht für Templates.
    Nutzt den Thread-Cache, um GlobalSettings nicht doppelt zu laden.
    """
    settings_obj = get_global_settings()
    return {
        "maintenance_mode_enabled": bool(
            settings_obj and settings_obj.maintenance_mode_enabled
        ),
        "maintenance_message": (
            settings_obj.maintenance_message
            if settings_obj and settings_obj.maintenance_message
            else ""
        ),
    }
