from __future__ import annotations

from types import SimpleNamespace

from .models import GlobalSettings


DEFAULT_FEATURE_FLAGS = {
    "show_patch_notes": True,
    "show_feedback": True,
    "show_movement_report": True,
    "show_admin_history": True,
    "show_scheduled_exports": True,
    "show_mark_button": False,
    "show_favorites": True,
    "enable_bulk_actions": True,
    "enable_attachments": True,
    "enable_image_upload": True,
    "enable_image_library": True,
    "enable_qr_actions": True,
    "enable_nfc_fields": True,
}


def get_feature_flags() -> dict[str, bool]:
    flags = DEFAULT_FEATURE_FLAGS.copy()
    settings = GlobalSettings.objects.first()
    if settings:
        flags.update(
            {
                "show_patch_notes": settings.show_patch_notes,
                "show_feedback": settings.show_feedback,
                "show_movement_report": settings.show_movement_report,
                "show_admin_history": settings.show_admin_history,
                "show_scheduled_exports": settings.show_scheduled_exports,
                "show_mark_button": settings.show_mark_button,
                "show_favorites": settings.show_favorites,
                "enable_bulk_actions": settings.enable_bulk_actions,
                "enable_attachments": settings.enable_attachments,
                "enable_image_upload": settings.enable_image_upload,
                "enable_image_library": settings.enable_image_library,
                "enable_qr_actions": settings.enable_qr_actions,
                "enable_nfc_fields": settings.enable_nfc_fields,
            }
        )
    return flags


def get_feature_flags_namespace() -> SimpleNamespace:
    return SimpleNamespace(**get_feature_flags())
