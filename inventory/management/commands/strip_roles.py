# inventory/management/commands/strip_roles.py
#
# Räumt Rollen/Matrix temporär auf:
# - reaktiviert alle Overviews
# - lässt Gruppen (Administrator/Editor/User/Viewer) bestehen, aber ohne Einfluss
#   (optional: Auskommentierte Zeilen aktivieren, wenn du Gruppen löschen willst)

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from inventory.models import Overview

DEFAULT_GROUPS = ["Administrator", "Editor", "User", "Viewer"]

class Command(BaseCommand):
    help = "Entfernt temporär alle Seiten-/Matrix-Rechte und Gruppen-Sichtbarkeiten (Overviews), ohne Superuser anzutasten."

    def handle(self, *args, **options):
        # 1) Overviews: aktivieren
        cnt = 0
        for ov in Overview.objects.all():
            ov.is_active = True
            ov.save()
            cnt += 1
        self.stdout.write(self.style.SUCCESS(f"Overviews bereinigt/aktiviert: {cnt}"))

        # 2) Optionale Gruppenbereinigung (deaktiviert):
        # for gname in DEFAULT_GROUPS:
        #     Group.objects.filter(name=gname).delete()
        # self.stdout.write(self.style.WARNING("Standardgruppen gelöscht (optional Schritt aktiviert)."))

        self.stdout.write(self.style.SUCCESS("Fertig. Jetzt greift der utils.py-Bypass für eingeloggte Nutzer."))
