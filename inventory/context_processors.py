from .feature_flags import get_feature_flags_namespace
from .models import GlobalSettings, Overview

def active_overviews(request):
    """
    Liefert alle aktiven Overviews in jedem Template-Kontext,
    falls global benötigt (z. B. für eine Sidebar).
    """
    return {"active_overviews": Overview.objects.filter(is_active=True)}


def global_features(request):
    """
    Liefert globale Feature-Schalter für Templates.
    """
    return {"global_features": get_feature_flags_namespace()}


def maintenance_status(request):
    """
    Liefert Wartungsmodus-Status und Nachricht für Templates.
    """
    settings_obj = GlobalSettings.objects.first()
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
