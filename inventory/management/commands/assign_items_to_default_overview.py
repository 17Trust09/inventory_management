from django.core.management.base import BaseCommand, CommandError
from inventory.models import InventoryItem, Overview


class Command(BaseCommand):
    help = "Weist allen Items ohne Dashboard ein bestimmtes Overview zu"

    def add_arguments(self, parser):
        parser.add_argument(
            "overview_slug",
            type=str,
            help="Slug des Ziel-Dashboards (z.B. mile-lager)",
        )

        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Nur Items verschieben, die noch KEIN Overview haben",
        )

    def handle(self, *args, **options):
        slug = options["overview_slug"]
        only_empty = options["only_empty"]

        try:
            overview = Overview.objects.get(slug=slug, is_active=True)
        except Overview.DoesNotExist:
            raise CommandError(f"Overview mit slug '{slug}' nicht gefunden oder inaktiv.")

        qs = InventoryItem.objects.all()

        if only_empty:
            qs = qs.filter(overview__isnull=True)

        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("Keine Items zum Verschieben gefunden."))
            return

        qs.update(overview=overview)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {total} Items wurden dem Dashboard '{overview.name}' zugewiesen."
            )
        )
