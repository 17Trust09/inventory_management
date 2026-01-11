# inventory/templatetags/group_tags.py
from django import template

register = template.Library()

@register.filter
def in_group(user, group_name: str) -> bool:
    """
    Ehemalige Gruppenprüfung.
    Jetzt immer False, da Rollen/Gruppen nicht mehr genutzt werden.
    """
    return False
