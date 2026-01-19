from __future__ import annotations

from types import SimpleNamespace

from .models import GlobalSettings


DEFAULT_FEATURE_FLAGS = {
    "show_patch_notes": True,
    "show_feedback": True,
    "show_movement_report": True,
    "show_admin_history": True,
    "show_scheduled_exports": True,
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
            }
        )
    return flags


def get_feature_flags_namespace() -> SimpleNamespace:
    return SimpleNamespace(**get_feature_flags())
