from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.admin_views import _create_backup, _get_global_settings, _prune_backups


class Command(BaseCommand):
    help = "Erstellt ein geplantes Backup, wenn das Intervall erreicht ist."

    def handle(self, *args, **options):
        settings_obj = _get_global_settings()
        interval_days = settings_obj.backup_interval_days
        if interval_days <= 0:
            self.stdout.write("Automatische Backups sind deaktiviert.")
            return

        last_backup = settings_obj.last_backup_at
        if last_backup:
            delta = timezone.now() - last_backup
            if delta.days < interval_days:
                self.stdout.write("Backup-Intervall noch nicht erreicht.")
                return

        ok, message = _create_backup()
        if ok:
            pruned = _prune_backups(settings_obj.backup_retention_count)
            self.stdout.write(message)
            if pruned:
                self.stdout.write(f"{pruned} alte Backups gelöscht.")
        else:
            self.stderr.write(message)
