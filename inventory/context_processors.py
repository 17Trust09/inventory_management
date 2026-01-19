from .feature_flags import get_feature_flags_namespace
from .models import Overview

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
