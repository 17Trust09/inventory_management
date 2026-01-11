# inventory_management/admin_site.py

from django.contrib.admin import AdminSite

class SuperuserAdminSite(AdminSite):
    site_header = "Django Admin (nur Superuser)"
    site_title = "Superuser Admin"
    index_title = "Willkommen, Superuser"

    def has_permission(self, request):
        # Nur aktive Superuser dürfen rein
        return bool(request.user.is_active and request.user.is_superuser)

# Instanz, die du in urls.py einbindest
superuser_admin_site = SuperuserAdminSite(name='superuser_admin')
