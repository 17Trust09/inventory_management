"""inventory_management URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from inventory import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/mark-item/<int:item_id>/', views.MarkItemAPI.as_view(), name='mark-item-api'),
    path('', include('inventory.urls'))
]
