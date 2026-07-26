# Re-Export aller Admin-View-Klassen und -Funktionen für admin_urls.py-Kompatibilität
# admin_urls.py importiert weiterhin aus inventory.admin_views
from .helpers import (
    _is_staff_or_super, _is_superuser,
    staff_required, superuser_required,
    StaffRequiredMixin, SuperuserRequiredMixin,
    _feature_enabled, _get_global_settings,
    _get_tailscale_status,
    ApplicationTagForm, CategoryForm,
)
from .dashboard import dashboard
from .categories import admin_categories_overview, CategoryCreateView, CategoryUpdateView, CategoryDeleteView, admin_pending_category_approve
from .tags import admin_tags_overview, ApplicationTagCreateView, ApplicationTagUpdateView, ApplicationTagDeleteView, admin_pending_tag_approve
from .items import InventoryItemListView, admin_item_edit, admin_item_delete, BorrowedItemListView, admin_qr_codes_view
from .users import (
    admin_userprofile_edit, admin_user_toggle_active,
    admin_userprofile_delete, UserProfileListView,
    _ensure_profile,
)
from .settings import GlobalSettingsListView, admin_globalsettings_edit, admin_feature_toggles
from .storages import (
    StorageLocationListView, StorageLocationCreateView,
    StorageLocationUpdateView, StorageLocationDeleteView,
    admin_storagelocation_regenerate_nfc,
)
from .system import (
    admin_system_status, admin_tailscale_setup, admin_esp32_setup, admin_updates,
    fetch_all_branches, _get_backup_root, _get_external_backup_paths,
    _get_backup_entries, _create_backup, _prune_backups, _restore_backup,
)
from .history import admin_history_list, admin_history_rollback
from .overviews import OverviewListView, admin_overview_create, admin_overview_edit, admin_overview_delete, admin_overview_approve
from .feedback import admin_feedback_set_status
from .import_export import admin_import_export

# TagType CRUD
from .tags import (
    TagTypeListView, TagTypeCreateView, TagTypeUpdateView, TagTypeDeleteView,
)

# Permission-Matrix (Legacy – noch nicht aufgeteilt)
from .permissions import permissions_matrix, toggle_permission, admin_manage_roles, admin_user_roles_edit, admin_user_delete_legacy

__all__ = [
    "dashboard",
    "_is_staff_or_super", "_is_superuser",
    "staff_required", "superuser_required",
    "StaffRequiredMixin", "SuperuserRequiredMixin",
    "_feature_enabled", "_get_global_settings",
    "_get_tailscale_status",
    "ApplicationTagForm", "CategoryForm",
    "CategoryCreateView", "CategoryUpdateView", "CategoryDeleteView",
    "admin_categories_overview",
    "admin_tags_overview",
    "ApplicationTagCreateView", "ApplicationTagUpdateView", "ApplicationTagDeleteView",
    "TagTypeListView", "TagTypeCreateView", "TagTypeUpdateView", "TagTypeDeleteView",
    "InventoryItemListView", "admin_item_edit", "admin_item_delete",
    "BorrowedItemListView", "admin_qr_codes_view",
    "admin_userprofile_edit", "admin_user_toggle_active",
    "admin_userprofile_delete", "UserProfileListView",
    "_ensure_profile",
    "GlobalSettingsListView", "admin_globalsettings_edit", "admin_feature_toggles",
    "StorageLocationListView", "StorageLocationCreateView",
    "StorageLocationUpdateView", "StorageLocationDeleteView",
    "admin_storagelocation_regenerate_nfc",
    "admin_system_status", "admin_tailscale_setup", "admin_esp32_setup",
    "admin_updates", "fetch_all_branches",
    "_get_backup_root", "_get_external_backup_paths",
    "_get_backup_entries", "_create_backup", "_prune_backups", "_restore_backup",
    "admin_history_list", "admin_history_rollback",
    "OverviewListView", "admin_overview_create", "admin_overview_edit",
    "admin_overview_delete", "admin_overview_approve",
    "admin_feedback_set_status", "admin_import_export",
    "permissions_matrix", "toggle_permission", "admin_manage_roles",
    "admin_user_roles_edit", "admin_user_delete_legacy",
]
