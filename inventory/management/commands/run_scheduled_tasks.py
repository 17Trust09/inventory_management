from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Führt geplante Hintergrundaufgaben (Backups/Exporte) aus."

    def handle(self, *args, **options):
        call_command("run_scheduled_backups")
        call_command("run_scheduled_exports")
