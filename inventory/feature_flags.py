from __future__ import annotations

from types import SimpleNamespace

from .utils import get_global_settings

# Nur diese Felder aus GlobalSettings gelten als Feature-Flags.
# Alle BooleanField-Namen, die NICHT in diesem Set sind, werden ignoriert
# (z. B. tailscale_setup_complete, maintenance_mode_enabled).
FEATURE_FLAG_FIELDS = {
    "show_patch_notes",
    "show_feedback",
    "show_movement_report",
    "show_admin_history",
    "show_scheduled_exports",
    "show_mark_button",
    "show_favorites",
    "show_system_settings",
    "enable_user_overview_requests",
    "enable_bulk_actions",
    "enable_item_move",
    "enable_item_history",
    "enable_attachments",
    "enable_image_upload",
    "enable_image_library",
    "enable_qr_actions",
    "enable_nfc_fields",
    "enable_unit_fields",
}

DEFAULT_FEATURE_FLAGS = {
    "show_patch_notes": True,
    "show_feedback": True,
    "show_movement_report": True,
    "show_admin_history": True,
    "show_scheduled_exports": True,
    "show_mark_button": False,
    "show_favorites": True,
    "show_system_settings": True,
    "enable_user_overview_requests": False,
    "enable_bulk_actions": True,
    "enable_item_move": True,
    "enable_item_history": True,
    "enable_attachments": True,
    "enable_image_upload": True,
    "enable_image_library": True,
    "enable_qr_actions": True,
    "enable_nfc_fields": True,
    "enable_unit_fields": True,
}


def get_feature_flags() -> dict[str, bool]:
    """
    Baut das Feature-Flags-Dict aus DEFAULT_FEATURE_FLAGS
    und überschreibt mit Werten aus DB (GlobalSettings), falls vorhanden.
    Neue Boolean-Felder in GlobalSettings werden automatisch erkannt,
    sobald sie in FEATURE_FLAG_FIELDS aufgenommen werden.
    """
    flags = DEFAULT_FEATURE_FLAGS.copy()
    settings = get_global_settings()
    if settings:
        for field_name in FEATURE_FLAG_FIELDS:
            if hasattr(settings, field_name):
                flags[field_name] = getattr(settings, field_name)
    return flags


def get_feature_flags_namespace() -> SimpleNamespace:
    return SimpleNamespace(**get_feature_flags())
