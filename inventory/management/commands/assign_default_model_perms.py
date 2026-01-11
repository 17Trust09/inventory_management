from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from inventory.models import InventoryItem

ROLE_ORDER = ['Superuser', 'Administrator', 'Editor', 'User', 'Viewer']


class Command(BaseCommand):
    help = "Weist Standard-Model-Permissions für Gruppen zu (z. B. add/change/delete/view auf InventoryItem)."

    def handle(self, *args, **options):
        # 1) Gruppen sicherstellen
        groups = {}
        for name in ROLE_ORDER:
            groups[name], _ = Group.objects.get_or_create(name=name)

        # 2) Relevante Permissions zu InventoryItem auflösen
        ct = ContentType.objects.get_for_model(InventoryItem)

        perm_codes = {
            'view': f'view_{InventoryItem._meta.model_name}',     # view_inventoryitem
            'add': f'add_{InventoryItem._meta.model_name}',       # add_inventoryitem
            'change': f'change_{InventoryItem._meta.model_name}', # change_inventoryitem
            'delete': f'delete_{InventoryItem._meta.model_name}', # delete_inventoryitem
        }

        perms = {
            key: Permission.objects.get(content_type=ct, codename=code)
            for key, code in perm_codes.items()
        }

        # 3) Zuweisungslogik:
        # - Administrator, Editor: alle 4 Rechte
        # - User, Viewer: nur view
        admin_like = ['Administrator', 'Editor']
        view_only = ['User', 'Viewer']

        for role in admin_like:
            grp = groups[role]
            to_set = [perms['view'], perms['add'], perms['change'], perms['delete']]
            for p in to_set:
                grp.permissions.add(p)
            self.stdout.write(self.style.SUCCESS(f"{role}: view/add/change/delete vergeben."))

        for role in view_only:
            grp = groups[role]
            # Erst alte Rechte entfernen, dann nur view setzen (optional, aber sauber)
            for p in [perms['add'], perms['change'], perms['delete']]:
                grp.permissions.remove(p)
            grp.permissions.add(perms['view'])
            self.stdout.write(self.style.SUCCESS(f"{role}: nur view vergeben."))

        self.stdout.write(self.style.SUCCESS("Fertig. Gruppen-Model-Permissions aktualisiert."))
