# inventory/utils.py
#
# Vereinfachte Zugriffskontrolle:
# - Nur Login ist nötig. Es gibt KEINE rollen- oder seitenbasierte Prüfung mehr.
# - Decorator und Mixin bleiben bestehen, damit bestehender Code unverändert funktioniert.

from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def page_view_permission_required(view_func):
    """
    Decorator für Funktions-Views: erzwingt ausschließlich Login.
    Nach erfolgreichem Login gibt es KEINE weitere Rechteprüfung.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Bitte melde dich an.")
            return redirect("login")
        # Nach Login immer erlauben
        return view_func(request, *args, **kwargs)
    return _wrapped


class PageViewPermissionRequiredMixin(LoginRequiredMixin):
    """
    Mixin für Class-Based-Views: erzwingt ausschließlich Login.
    Nach erfolgreichem Login gibt es KEINE weitere Rechteprüfung.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Bitte melde dich an.")
            return redirect("login")
        # Nach Login immer erlauben
        return super().dispatch(request, *args, **kwargs)
