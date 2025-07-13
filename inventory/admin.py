from django.contrib import admin
from .models import InventoryItem, Category

class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'category', 'location_letter', 'location_number')

admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Category)
