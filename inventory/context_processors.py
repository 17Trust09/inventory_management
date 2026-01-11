from .models import Overview

def active_overviews(request):
    """
    Liefert alle aktiven Overviews in jedem Template-Kontext,
    falls global benötigt (z. B. für eine Sidebar).
    """
    return {"active_overviews": Overview.objects.filter(is_active=True)}
