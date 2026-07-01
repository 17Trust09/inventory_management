"""
Admin-Helper-Funktionen: Auth-Prüfungen, Forms, Tailscale-Status.
"""
import json
import os
import shutil
import subprocess
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django import forms

from ..models import (
    ApplicationTag, Category, GlobalSettings,
)
from ..feature_flags import get_feature_flags

logger = __import__('logging').getLogger(__name__)


def _is_staff_or_super(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _is_superuser(user):
    return user.is_authenticated and user.is_superuser


def staff_required(view_func):
    return user_passes_test(_is_staff_or_super, login_url="login")(view_func)


def superuser_required(view_func):
    return user_passes_test(_is_superuser, login_url="login")(view_func)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return _is_staff_or_super(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Kein Zugriff. Bitte als Admin anmelden.")
        return redirect("login")


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return _is_superuser(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Kein Zugriff. Bitte als Superuser anmelden.")
        return redirect("login")


def _feature_enabled(flag_name: str) -> bool:
    return get_feature_flags().get(flag_name, True)


def _get_global_settings() -> GlobalSettings:
    settings_obj = GlobalSettings.objects.first()
    if not settings_obj:
        settings_obj = GlobalSettings.objects.create()
    return settings_obj


def _get_tailscale_status() -> dict[str, str | bool | list[str] | None]:
    tailscale_path = shutil.which(
        "tailscale",
        path=":".join([
            os.getenv("PATH", ""),
            "/usr/local/sbin", "/usr/local/bin",
            "/usr/sbin", "/usr/bin",
            "/sbin", "/bin",
        ]),
    )
    if tailscale_path is None:
        return {"installed": False, "connected": False, "error": "Tailscale ist nicht installiert.", "backend_state": None, "hostname": None, "dns_name": None, "ips": []}
    try:
        result = subprocess.run([tailscale_path, "status", "--json"], capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        return {"installed": True, "connected": False, "error": "Tailscale-Status hat zu lange gedauert.", "backend_state": None, "hostname": None, "dns_name": None, "ips": []}
    if result.returncode != 0:
        return {"installed": True, "connected": False, "error": result.stderr.strip() or result.stdout.strip() or "Status konnte nicht gelesen werden.", "backend_state": None, "hostname": None, "dns_name": None, "ips": []}
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    self_node = data.get("Self", {}) if isinstance(data, dict) else {}
    backend_state = data.get("BackendState") if isinstance(data, dict) else None
    ips = self_node.get("TailscaleIPs") or []
    if not isinstance(ips, list):
        ips = []
    return {"installed": True, "connected": backend_state == "Running", "error": None, "backend_state": backend_state, "hostname": self_node.get("HostName"), "dns_name": self_node.get("DNSName"), "ips": ips}


class ApplicationTagForm(forms.ModelForm):
    class Meta:
        model = ApplicationTag
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control form-control-lg'})}
        labels = {'name': 'Tag-Name'}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = self.fields['name'].widget.attrs.get('class', '')
        if 'form-control' not in css:
            self.fields['name'].widget.attrs['class'] = (css + ' form-control form-control-lg').strip()


__all__ = [
    "_is_staff_or_super", "_is_superuser", "staff_required", "superuser_required",
    "StaffRequiredMixin", "SuperuserRequiredMixin",
    "_feature_enabled", "_get_global_settings", "_get_tailscale_status",
    "ApplicationTagForm", "CategoryForm",
]
