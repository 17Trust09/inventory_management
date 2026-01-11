# inventory_management/urls.py

"""inventory_management URL Configuration"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from inventory import views
from .admin_site import superuser_admin_site  # importiere die Instanz, nicht die Klasse

urlpatterns = [
    # 🔧 Custom Admin (nur Superuser)
    path('admin/', superuser_admin_site.urls),

    # 🔄 API-Endpunkt für externe Steuerung
    path('api/mark-item/<int:item_id>/', views.MarkItemAPI.as_view(), name='mark-item-api'),

    # 🌐 App-Routen
    path('', include('inventory.urls')),
]

# 🖼️ Medien-Dateien im Debug-Modus bereitstellen
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
