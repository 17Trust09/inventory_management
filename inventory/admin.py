from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from .models import (
    InventoryItem, Category, ApplicationTag, UserProfile, GlobalSettings, QRCodeOverviewModel
)


# ✅ QR-Code Übersicht im Admin (leitet auf eigene View um)
class QRCodeOverview(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('admin-qr-codes'))  # Eigene View-URL

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


# 🧩 Verwaltung der Inventarartikel
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'category', 'location_letter', 'location_number', 'qr_code_link')
    search_fields = ('name',)
    list_filter = ('category', 'location_letter')

    def qr_code_link(self, obj):
        if obj.id:
            return format_html(
                '<a href="/media/qrcodes/qr_{}.jpg" target="_blank">QR anzeigen</a>', obj.id
            )
        return "-"
    qr_code_link.short_description = "QR-Code"


# 🧩 Verwaltung Benutzer-Tag-Zuordnung
class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple
        }


class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user',)
    filter_horizontal = ('tags',)


# 🧩 Anwendungstags (z. B. Arbeit, Licht, etc.)
class ApplicationTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or obj.name != "-")


# 🧩 Globale Einstellung (z. B. Basis-URL für QR-Codes)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ('qr_base_url',)

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ✅ Admin-Registrierung
admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Category)
admin.site.register(ApplicationTag, ApplicationTagAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(GlobalSettings, GlobalSettingsAdmin)
admin.site.register(QRCodeOverviewModel, QRCodeOverview)
