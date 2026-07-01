# inventory/apps.py

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Signals für UserProfile-Erstellung und Default-Tag/-Group laden
        import inventory.signals
        import inventory.checks

        # GlobalSettings-Thread-Cache bei jedem Request-Start leeren
        from django.core.signals import request_started
        from .threadlocal import clear_global_settings_cache
        request_started.connect(
            lambda **kwargs: clear_global_settings_cache(),
            dispatch_uid="clear_global_settings_cache",
        )
