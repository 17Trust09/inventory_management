# inventory/management/commands/strip_roles.py
#
# Räumt Rollen/Matrix temporär auf:
# - löscht alle RolePermission-Einträge
# - leert visible_for_groups bei allen Overviews
# - lässt Gruppen (Administrator/Editor/User/Viewer) bestehen, aber ohne Einfluss
#   (optional: Auskommentierte Zeilen aktivieren, wenn du Gruppen löschen willst)

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from inventory.models import RolePermission, Overview

DEFAULT_GROUPS = ["Administrator", "Editor", "User", "Viewer"]

class Command(BaseCommand):
    help = "Entfernt temporär alle Seiten-/Matrix-Rechte und Gruppen-Sichtbarkeiten (Overviews), ohne Superuser anzutasten."

    def handle(self, *args, **options):
        # 1) RolePermission leeren
        deleted, _ = RolePermission.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"RolePermission gelöscht: {deleted} Einträge"))

        # 2) Overviews: Sichtbarkeiten neutralisieren
        cnt = 0
        for ov in Overview.objects.all():
            ov.visible_for_groups.clear()
            ov.is_active = True
            ov.save()
            cnt += 1
        self.stdout.write(self.style.SUCCESS(f"Overviews bereinigt/aktiviert: {cnt}"))

        # 3) Optionale Gruppenbereinigung (deaktiviert):
        # for gname in DEFAULT_GROUPS:
        #     Group.objects.filter(name=gname).delete()
        # self.stdout.write(self.style.WARNING("Standardgruppen gelöscht (optional Schritt aktiviert)."))

        self.stdout.write(self.style.SUCCESS("Fertig. Jetzt greift der utils.py-Bypass für eingeloggte Nutzer."))
