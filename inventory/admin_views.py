from django.shortcuts import render
from .models import InventoryItem
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_qr_codes_view(request):
    items_with_qr = InventoryItem.objects.all()
    return render(request, 'inventory/admin_qr_overview.html', {'items': items_with_qr})
