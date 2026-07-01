"""
Admin GlobalSettings: Liste, Edit, Feature-Toggles.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView
from django.contrib import messages
from django import forms

from ..models import GlobalSettings
from .helpers import staff_required, superuser_required, StaffRequiredMixin


class GlobalSettingsListView(StaffRequiredMixin, ListView):
    model = GlobalSettings
    template_name = 'inventory/admin_globalsettings_list.html'
    context_object_name = 'settings'

    def get_queryset(self):
        qs = super().get_queryset()
        if not qs.exists():
            GlobalSettings.objects.create()
            qs = super().get_queryset()
        return qs


@staff_required
def admin_globalsettings_edit(request, pk):
    gs = get_object_or_404(GlobalSettings, pk=pk)

    class GSForm(forms.ModelForm):
        class Meta:
            model = GlobalSettings
            fields = ['qr_base_url', 'nfc_base_url_local', 'nfc_base_url_remote']
            widgets = {
                'qr_base_url': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'nfc_base_url_local': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
                'nfc_base_url_remote': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            }
            labels = {
                'qr_base_url': 'Basis-URL für QR-Code-Links',
                'nfc_base_url_local': 'NFC-Basis-URL (Lokal)',
                'nfc_base_url_remote': 'NFC-Basis-URL (Tailscale/Remote)',
            }
            help_texts = {
                'qr_base_url': 'z. B. http://192.168.178.20:8000',
                'nfc_base_url_local': 'z. B. http://192.168.178.20:8000',
                'nfc_base_url_remote': 'z. B. https://host.tailnet-xyz.ts.net',
            }

    if request.method == 'POST':
        form = GSForm(request.POST, instance=gs)
        if form.is_valid():
            form.save()
            messages.success(request, "Globale Einstellungen gespeichert.")
            return redirect('admin_global_settings')
    else:
        form = GSForm(instance=gs)
    return render(request, 'inventory/admin_globalsettings_form.html', {'form': form})


@superuser_required
def admin_feature_toggles(request):
    settings = GlobalSettings.objects.first()
    if not settings:
        settings = GlobalSettings.objects.create()

    class FeatureToggleForm(forms.ModelForm):
        class Meta:
            model = GlobalSettings
            fields = [
                "show_patch_notes", "show_feedback", "show_movement_report",
                "show_admin_history", "show_scheduled_exports", "show_mark_button",
                "show_favorites", "show_system_settings",
                "enable_user_overview_requests", "enable_bulk_actions",
                "enable_item_move", "enable_item_history", "enable_attachments",
                "enable_image_upload", "enable_image_library",
                "enable_qr_actions", "enable_nfc_fields", "enable_unit_fields",
            ]
            labels = {
                "show_patch_notes": "Patch Notes",
                "show_feedback": "Feedback-Board",
                "show_movement_report": "Lagerbewegungen",
                "show_admin_history": "Historie & Rollback (Admin)",
                "show_scheduled_exports": "Geplante Exporte",
                "show_mark_button": "Markieren-Button im Dashboard",
                "show_favorites": "Favoriten & Schnellzugriff",
                "show_system_settings": "System-Einstellungen anzeigen",
                "enable_user_overview_requests": "Dashboard-Anfragen durch Benutzer erlauben",
                "enable_bulk_actions": "Bulk-Aktionen",
                "enable_item_move": "Item in anderes Dashboard verschieben",
                "enable_item_history": "Verlauf & Timeline im Item-Edit",
                "enable_attachments": "Dokumente/Bilder (Anhänge)",
                "enable_image_upload": "Bild-Upload",
                "enable_image_library": "Bild-Bibliothek",
                "enable_qr_actions": "QR-Aktionen",
                "enable_nfc_fields": "NFC-Felder",
                "enable_unit_fields": "Einheit anzeigen",
            }

    if request.method == "POST":
        form = FeatureToggleForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Feature-Schalter wurden gespeichert.")
            return redirect("admin_feature_toggles")
    else:
        form = FeatureToggleForm(instance=settings)
    return render(request, "inventory/admin_feature_toggles.html", {"form": form})
