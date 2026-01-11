# inventory/templatetags/ha_status.py
from __future__ import annotations

from django import template
from inventory.integrations.homeassistant import get_status_tuple

register = template.Library()


@register.inclusion_tag("inventory/partials/ha_status_badge.html", takes_context=False)
def ha_status_badge():
    """
    Kleines Badge für die UI mit Online/Offline-Status:
    - "Feedbacks werden online übertragen"
    - "Keine Internet-Verbindung ..."
    (Ergebnis ist 60s gecacht in der Integration.)
    """
    available, message = get_status_tuple()
    return {"available": available, "message": message}
