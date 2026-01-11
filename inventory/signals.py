# inventory/signals.py
from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User, Group
from django.dispatch import receiver

from .models import UserProfile, Feedback, FeedbackComment
from .integrations.homeassistant import notify_feedback_event


# ──────────────────────────────────────────────────────────────────────────────
# User: erster User → Superuser
# ──────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def make_first_user_superuser(sender, instance, created, **kwargs):
    """
    Der allererste registrierte Benutzer wird automatisch Staff + Superuser.
    """
    if created and User.objects.count() == 1:
        instance.is_staff = True
        instance.is_superuser = True
        instance.save(update_fields=["is_staff", "is_superuser"])


# ──────────────────────────────────────────────────────────────────────────────
# User: bei Neuanlage Profil + Default-Gruppe
# ──────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def create_user_profile_and_assign_defaults(sender, instance, created, **kwargs):
    """
    Für jeden neuen User:
      1) Ein UserProfile anlegen (falls nicht vorhanden).
      2) In die Default-Gruppe 'User' stecken.
      3) Keine Tags, keine Overviews per Default (=> kein Dashboard-Zugriff).
    """
    if not created:
        return

    # 1) Profil sicherstellen
    UserProfile.objects.get_or_create(user=instance)

    # 2) Default-Gruppe 'User'
    default_group, _ = Group.objects.get_or_create(name="User")
    instance.groups.add(default_group)


# ──────────────────────────────────────────────────────────────────────────────
# Feedback → Home Assistant
#   - created           → "created"
#   - status geändert   → "status_changed" (+ old_status / old_status_display)
#   - sonstiges Update  → "updated" (+ changed Felder)
#   - Kommentar neu     → "comment_added" (+ author / comment)
# ──────────────────────────────────────────────────────────────────────────────

@receiver(pre_save, sender=Feedback)
def _feedback_pre_save(sender, instance: Feedback, **kwargs):
    """
    Vor dem Speichern: alten Zustand laden, um Änderungen erkennen zu können.
    (post_save allein weiß nicht, was sich geändert hat.)
    """
    if not instance.pk:
        return  # neu – kein Vorzustand

    try:
        old = Feedback.objects.get(pk=instance.pk)
    except Feedback.DoesNotExist:
        return

    # für post_save merken
    instance._old_status = old.status  # type: ignore[attr-defined]

    changed: set[str] = set()
    if old.title != instance.title:
        changed.add("title")
    if old.description != instance.description:
        changed.add("description")
    # assignee kann None sein → IDs vergleichen
    if (old.assignee_id or None) != (instance.assignee_id or None):
        changed.add("assignee")

    instance._changed_fields = changed  # type: ignore[attr-defined]


@receiver(post_save, sender=Feedback)
def _feedback_post_save(sender, instance: Feedback, created: bool, **kwargs):
    """
    Nach dem Speichern: Event an HA schicken.
    """
    try:
        if created:
            # Neues Feedback
            notify_feedback_event("created", instance)
            return

        # Statuswechsel?
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            # Anzeige-Label für alten Status ermitteln
            status_display_map = dict(Feedback.Status.choices)
            extra = {
                "old_status": old_status,
                "old_status_display": status_display_map.get(old_status, old_status),
            }
            notify_feedback_event("status_changed", instance, extra=extra)
            return

        # Sonstige inhaltliche Änderung?
        changed = list(getattr(instance, "_changed_fields", []) or [])
        if changed:
            notify_feedback_event("updated", instance, extra={"changed": sorted(changed)})
    except Exception as e:
        # Wir lassen die App niemals wegen einer Benachrichtigung abstürzen.
        print(f"[signals] notify_feedback_event Fehler: {e}")


@receiver(post_save, sender=FeedbackComment)
def _feedback_comment_post_save(sender, instance: FeedbackComment, created: bool, **kwargs):
    """
    Neuer Kommentar → Event an HA.
    """
    if not created:
        return

    try:
        extra = {
            "author": getattr(instance.author, "username", None),
            "comment": instance.text or "",
        }
        notify_feedback_event("comment_added", instance.feedback, extra=extra)
    except Exception as e:
        print(f"[signals] notify_feedback_event(comment) Fehler: {e}")
