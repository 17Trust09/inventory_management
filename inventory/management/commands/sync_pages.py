# inventory/management/commands/sync_pages.py

import sys
from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLResolver, URLPattern
from django.db import IntegrityError, transaction
from inventory.models import Page

class Command(BaseCommand):
    help = "Synchronisiert alle Pages aus dem inventory-Modul und entfernt verwaiste Einträge"

    def handle(self, *args, **options):
        resolver = get_resolver()

        def flatten(patterns):
            for p in patterns:
                if isinstance(p, URLResolver):
                    yield from flatten(p.url_patterns)
                elif isinstance(p, URLPattern):
                    yield p

        # 1) Sammle alle benannten Patterns, deren Callback im inventory-Package liegt
        all_patterns = [
            p for p in flatten(resolver.url_patterns)
            if p.name and p.callback.__module__.startswith('inventory.')
        ]
        found_names = {p.name for p in all_patterns}

        created = 0
        for pat in all_patterns:
            url_name = pat.name
            base_name = url_name.replace('_', ' ').title()

            # Falls dieser Anzeigename schon von einer anderen URL vergeben ist,
            # erweitere um "(url_name)"
            if Page.objects.filter(name=base_name).exclude(url_name=url_name).exists():
                human_name = f"{base_name} ({url_name})"
            else:
                human_name = base_name

            # Versuche Update oder Create innerhalb eines kleinen Transactionsblocks
            try:
                with transaction.atomic():
                    page_obj, was_created = Page.objects.update_or_create(
                        url_name=url_name,
                        defaults={
                            'name': human_name,
                            'example_kwargs': {}
                        }
                    )
            except IntegrityError as e:
                self.stdout.write(self.style.ERROR(
                    f"FEHLER bei {url_name}: {e}"
                ))
                continue

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Neu: {url_name} → {human_name}"))

        # Verwaiste Pages melden/löschen (optional – hier nur Info)
        stale = Page.objects.exclude(url_name__in=found_names)
        if stale.exists():
            self.stdout.write(f"{stale.count()} verwaiste Pages vorhanden (werden beibehalten).")

        self.stdout.write(self.style.SUCCESS(f"Fertig – {created} neue Pages angelegt/aktualisiert."))
