from django.conf import settings
from django.core.checks import Error, register

from .patch_notes import CURRENT_VERSION, PATCH_NOTES


@register()
def patch_notes_check(app_configs, **kwargs):
    errors = []
    if not PATCH_NOTES:
        errors.append(
            Error(
                "PATCH_NOTES ist leer. Bitte mindestens einen Eintrag pflegen.",
                id="inventory.E001",
            )
        )
        return errors

    latest = PATCH_NOTES[0]
    if latest.get("version") != CURRENT_VERSION:
        errors.append(
            Error(
                "CURRENT_VERSION stimmt nicht mit der ersten Patch-Note überein.",
                id="inventory.E002",
            )
        )

    inventory_version = getattr(settings, "INVENTORY_VERSION", None)
    if inventory_version and inventory_version != CURRENT_VERSION:
        errors.append(
            Error(
                "INVENTORY_VERSION und PATCH_NOTES sind nicht synchron.",
                hint="Bitte INVENTORY_VERSION und die erste Patch-Note gleichzeitig aktualisieren.",
                id="inventory.E003",
            )
        )

    changes = latest.get("changes") or []
    if not changes:
        errors.append(
            Error(
                "Die neueste Patch-Note enthält keine Änderungen.",
                id="inventory.E004",
            )
        )

    return errors
