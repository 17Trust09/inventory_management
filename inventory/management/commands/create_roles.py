# inventory/management/commands/create_roles.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = "Erstellt die Rollen Viewer, Editor, Administrator und Superuser"

    def handle(self, *args, **options):
        app_label = 'inventory'
        perms = Permission.objects.filter(content_type__app_label=app_label)

        groups = {
            'Viewer': {
                'filter': lambda p: p.codename.startswith('view_')
            },
            'Editor': {
                'filter': lambda p: p.codename.startswith(('view_', 'add_', 'change_'))
            },
            'Administrator': {
                'filter': lambda p: p.codename.startswith(('view_', 'add_', 'change_', 'delete_'))
            },
            'Superuser': {
                'filter': lambda p: False  # keine Berechtigungen per Gruppe
            },
        }

        for name, cfg in groups.items():
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Gruppe „{name}“ angelegt."))
            else:
                self.stdout.write(f"Gruppe „{name}“ existierte bereits.")

            # Berechtigungen zuweisen (außer Superuser)
            selected = [p for p in perms if cfg['filter'](p)]
            group.permissions.set(selected)
            self.stdout.write(f"  -> {len(selected)} Permissions zugewiesen.")

        self.stdout.write(self.style.SUCCESS("Rollen-Gruppen wurden eingerichtet."))
