from django.contrib import admin
from django import forms
from .models import InventoryItem, Category, ApplicationTag, UserProfile


class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'category', 'location_letter', 'location_number')
    search_fields = ('name',)
    list_filter = ('category', 'location_letter')


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


class ApplicationTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or obj.name != "-")


admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Category)
admin.site.register(ApplicationTag, ApplicationTagAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
