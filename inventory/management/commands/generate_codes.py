# inventory/management/commands/generate_codes.py
#
# Erzeugt fehlende QR-/Barcode-Dateien für Items (optional erzwingen).

from django.core.management.base import BaseCommand
from inventory.models import InventoryItem


class Command(BaseCommand):
    help = "Erzeugt fehlende QR-/Barcode-Dateien für InventoryItems."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="QR-/Barcode-Dateien für alle Items neu generieren.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        total = 0
        regenerated = 0

        for item in InventoryItem.objects.all():
            total += 1
            needs_qr = not item.qr_exists
            if force or needs_qr:
                item.generate_codes_if_needed(is_new=force, regenerate_qr=True)
                regenerated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"QR-/Barcode-Generierung abgeschlossen: {regenerated}/{total} Items."
            )
        )
