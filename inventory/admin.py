# inventory/admin.py

from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.contrib import admin

# >>> NEU: Auth-Imports für User/Group im Custom-Admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from inventory_management.admin_site import superuser_admin_site
from .models import (
    InventoryItem,
    Category,
    ApplicationTag,
    UserProfile,
    GlobalSettings,
    QRCodeOverviewModel,
    BorrowedItem,
    TagType,
    Overview,  # NEU: modulares Dashboard
)

# ── Auth in Custom-Admin sichtbar machen ──────────────────────────────────────
# Falls bereits registriert, stillschweigend ignorieren.
try:
    superuser_admin_site.register(User, UserAdmin)
except admin.sites.AlreadyRegistered:
    pass

try:
    superuser_admin_site.register(Group, GroupAdmin)
except admin.sites.AlreadyRegistered:
    pass


# ── TagType ────────────────────────────────────────────────────────────────────
class TagTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


superuser_admin_site.register(TagType, TagTypeAdmin)


# ── QR-Code Übersicht im Admin (leitet auf eigene View um)────────────────────
class QRCodeOverviewAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('admin_qr_codes'))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


superuser_admin_site.register(QRCodeOverviewModel, QRCodeOverviewAdmin)


# ── InventoryItem ─────────────────────────────────────────────────────────────
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'quantity', 'category',
        'location_letter', 'location_number', 'qr_code_link'
    )
    search_fields = ('name',)
    list_filter = ('category', 'location_letter')

    def qr_code_link(self, obj):
        if obj.id:
            return format_html(
                '<a href="/media/qrcodes/qr_{}.jpg" target="_blank">QR anzeigen</a>', obj.id
            )
        return "-"
    qr_code_link.short_description = "QR-Code"


superuser_admin_site.register(InventoryItem, InventoryItemAdmin)


# ── Category ─────────────────────────────────────────────────────────────────
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


superuser_admin_site.register(Category, CategoryAdmin)


# ── ApplicationTag ────────────────────────────────────────────────────────────
class ApplicationTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    search_fields = ('name',)
    list_filter = ('type',)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or obj.name != "-")


superuser_admin_site.register(ApplicationTag, ApplicationTagAdmin)


# ── UserProfile ──────────────────────────────────────────────────────────────
# Wichtig: Tags sollen NICHT mehr im Admin bearbeitet werden.
# Es bleiben nur noch die erlaubten Dashboards (allowed_overviews).
class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # Nur diese Felder im Admin zeigen:
        fields = ('user', 'allowed_overviews')
        widgets = {
            'allowed_overviews': forms.CheckboxSelectMultiple,
        }


class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user',)
    # Früher: ('tags',) -> entfernt, stattdessen allowed_overviews
    filter_horizontal = ('allowed_overviews',)


superuser_admin_site.register(UserProfile, UserProfileAdmin)


# ── GlobalSettings ───────────────────────────────────────────────────────────
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ('qr_base_url',)

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


superuser_admin_site.register(GlobalSettings, GlobalSettingsAdmin)


# ── BorrowedItem ──────────────────────────────────────────────────────────────
@admin.action(description="✅ Als zurückgegeben markieren (inkl. Bestandskorrektur)")
def mark_as_returned(modeladmin, request, queryset):
    for borrowed in queryset.filter(returned=False):
        borrowed.item.quantity += borrowed.quantity_borrowed
        borrowed.item.save()
        borrowed.returned = True
        borrowed.returned_at = now()
        borrowed.save()


class BorrowedItemAdmin(admin.ModelAdmin):
    list_display = (
        'item', 'borrower', 'quantity_borrowed',
        'borrowed_at', 'returned', 'returned_at'
    )
    list_filter = ('returned', 'borrowed_at')
    search_fields = ('borrower', 'item__name')
    actions = [mark_as_returned]


superuser_admin_site.register(BorrowedItem, BorrowedItemAdmin)


# ── NEU: Overview (Modulares Dashboard) ──────────────────────────────────────
class OverviewAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = (
        "is_active",
        "show_quantity", "has_locations", "has_min_stock",
        "enable_borrow", "is_consumable_mode"
    )
    search_fields = ("name", "slug", "description")
    filter_horizontal = ("visible_for_groups", "categories")
    fieldsets = (
        ("Basis", {
            "fields": ("name", "slug", "description", "icon_emoji", "order", "is_active")
        }),
        ("Sichtbarkeit / Filter", {
            "fields": ("visible_for_groups", "categories")
        }),
        ("Features", {
            "fields": (
                "show_quantity", "has_locations", "has_min_stock",
                "enable_borrow", "is_consumable_mode", "require_qr"
            )
        }),
        ("Erweiterte Konfiguration", {
            "fields": ("config",)
        }),
    )


superuser_admin_site.register(Overview, OverviewAdmin)
