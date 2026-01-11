# inventory/apps.py

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Signals für UserProfile-Erstellung und Default-Tag/-Group laden
        import inventory.signals
