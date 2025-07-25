"""inventory_management URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from inventory import views

# Medien und statische Dateien im Debug-Modus (z. B. QR-Codes, Bilder)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🔧 Admin-Oberfläche
    path('admin/', admin.site.urls),

    # 🔄 API-Endpunkt für externe Steuerung (z. B. Home Assistant)
    path('api/mark-item/<int:item_id>/', views.MarkItemAPI.as_view(), name='mark-item-api'),

    # 🌐 App-Routen (z. B. /edit/1, /add-item usw.)
    path('', include('inventory.urls')),
]

# 🖼️ Medien-Dateien bereitstellen (z. B. /media/qrcodes/qr_1.jpg)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
