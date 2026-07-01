"""
Auth- und einfache Content-Views: Login, Signup, Index, PatchNotes, Barcode-Scan.
"""
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

from ..forms import UserRegisterForm
from ..feature_flags import get_feature_flags
from ..models import InventoryItem
from ..patch_notes import PATCH_NOTES, CURRENT_VERSION


class CustomAuthForm(AuthenticationForm):
    """Leicht angepasstes Login-Formular."""
    pass


class Index(TemplateView):
    template_name = "inventory/index.html"


class PatchNotesView(TemplateView):
    template_name = "inventory/patch_notes.html"

    def dispatch(self, request, *args, **kwargs):
        flags = get_feature_flags()
        if not flags.get("show_patch_notes", True):
            messages.error(request, "Patch Notes sind aktuell deaktiviert.")
            return redirect("dashboards")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["patch_notes"] = PATCH_NOTES
        ctx["current_version"] = CURRENT_VERSION
        return ctx


class SignUpView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, "inventory/signup.html", {"form": form})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            if User.objects.count() == 1:
                new_user.is_staff = True
                new_user.is_superuser = True
                new_user.save()
            try:
                viewer = Group.objects.get(name="Viewer")
                new_user.groups.set([viewer])
            except Group.DoesNotExist:
                pass
            user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
            )
            login(request, user)
            return redirect("index")
        return render(request, "inventory/signup.html", {"form": form})


class ScanBarcodeView(LoginRequiredMixin, View):
    def get(self, request):
        barcode = request.GET.get("code", "").strip()
        if barcode:
            item = InventoryItem.objects.filter(barcode=barcode).first()
            if item:
                return redirect("edit-item", pk=item.pk)
            messages.warning(request, f"Kein Artikel mit Barcode „{barcode}“ gefunden.")
        return render(request, "inventory/scan_input.html", {"barcode": barcode})


class BarcodeListView(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.filter(
            barcode__isnull=False
        ).exclude(barcode="").order_by("name")
        return render(request, "inventory/barcode_list.html", {"items": items})


__all__ = [
    "Index",
    "SignUpView",
    "CustomAuthForm",
    "PatchNotesView",
    "ScanBarcodeView",
    "BarcodeListView",
]
