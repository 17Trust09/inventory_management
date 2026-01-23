# inventory/admin_urls.py

from django.urls import path
from .admin_views import (
    # Dashboard
    dashboard,

    # Kategorien & Tags – Overviews (global)
    admin_categories_overview,
    admin_tags_overview,

    # Kategorien – einheitliches CRUD
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,

    # Tags – einheitliches CRUD
    ApplicationTagCreateView,
    ApplicationTagUpdateView,
    ApplicationTagDeleteView,

    # Items & Vorgänge
    InventoryItemListView,
    admin_item_edit,
    admin_item_delete,
    BorrowedItemListView,
    admin_qr_codes_view,
    admin_updates,
    admin_tailscale_setup,
    admin_system_status,

    # User Profiles
    UserProfileListView,
    admin_userprofile_edit,
    admin_user_toggle_active,     # NEU
    admin_userprofile_delete,     # NEU

    # Tag Types
    TagTypeListView,
    TagTypeCreateView,
    TagTypeUpdateView,
    TagTypeDeleteView,

    # Global Settings
    GlobalSettingsListView,
    admin_globalsettings_edit,
    admin_feature_toggles,

    # Storage Locations
    StorageLocationListView,
    StorageLocationCreateView,
    StorageLocationUpdateView,
    StorageLocationDeleteView,
    admin_storagelocation_regenerate_nfc,

    # Overviews (Dashboards)
    OverviewListView,
    admin_overview_create,
    admin_overview_edit,
    admin_overview_delete,

    # Feedback Quick-Action
    admin_feedback_set_status,

    # History
    admin_history_list,
    admin_history_rollback,
)

urlpatterns = [
    # Dashboard
    path('', dashboard, name='admin_dashboard'),

    # Kategorien (global) + einheitliche CRUD
    path('categories/', admin_categories_overview, name='admin_categories'),
    path('categories/add/', CategoryCreateView.as_view(), name='admin_category_add'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='admin_category_edit'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='admin_category_delete'),

    # Tags (global) + einheitliche CRUD
    path('tags/', admin_tags_overview, name='admin_tags_overview'),
    path('tags/add/', ApplicationTagCreateView.as_view(), name='admin_tag_add'),
    path('tags/<int:pk>/edit/', ApplicationTagUpdateView.as_view(), name='admin_tag_edit'),
    path('tags/<int:pk>/delete/', ApplicationTagDeleteView.as_view(), name='admin_tag_delete'),

    # Items & Vorgänge
    path('items/', InventoryItemListView.as_view(), name='admin_items'),
    path('items/<int:pk>/edit/', admin_item_edit, name='admin_item_edit'),
    path('items/<int:pk>/delete/', admin_item_delete, name='admin_item_delete'),
    path('borrowed-items/', BorrowedItemListView.as_view(), name='admin_borrowed_items'),
    path('qr-codes/', admin_qr_codes_view, name='admin_qr_codes'),
    path('updates/', admin_updates, name='admin_updates'),
    path('tailscale-setup/', admin_tailscale_setup, name='admin_tailscale_setup'),
    path('system-status/', admin_system_status, name='admin_system_status'),
    path('history/', admin_history_list, name='admin_history_list'),
    path('history/<int:pk>/rollback/', admin_history_rollback, name='admin_history_rollback'),

    # User Profiles
    path('profiles/', UserProfileListView.as_view(), name='admin_userprofiles_list'),
    path('profiles/list/', UserProfileListView.as_view(), name='admin_user_profiles'),  # Alias, falls Templates alt sind
    path('profiles/<int:pk>/edit/', admin_userprofile_edit, name='admin_userprofile_edit'),
    path('profiles/<int:pk>/toggle-active/', admin_user_toggle_active, name='admin_user_toggle_active'),  # NEU
    path('profiles/<int:pk>/delete/', admin_userprofile_delete, name='admin_userprofile_delete'),          # NEU

    # Tag Types
    path('tag-types/', TagTypeListView.as_view(), name='admin_tagtypes'),
    path('tag-types/add/', TagTypeCreateView.as_view(), name='admin_tagtype_add'),
    path('tag-types/<int:pk>/edit/', TagTypeUpdateView.as_view(), name='admin_tagtype_edit'),
    path('tag-types/<int:pk>/delete/', TagTypeDeleteView.as_view(), name='admin_tagtype_delete'),

    # Global Settings
    path('settings/', GlobalSettingsListView.as_view(), name='admin_global_settings'),
    path('settings/<int:pk>/edit/', admin_globalsettings_edit, name='admin_globalsettings_edit'),
    path('feature-toggles/', admin_feature_toggles, name='admin_feature_toggles'),

    # Storage Locations
    path('storage-locations/', StorageLocationListView.as_view(), name='admin_storagelocations'),
    path('storage-locations/add/', StorageLocationCreateView.as_view(), name='admin_storagelocation_add'),
    path('storage-locations/<int:pk>/edit/', StorageLocationUpdateView.as_view(), name='admin_storagelocation_edit'),
    path('storage-locations/<int:pk>/regenerate-nfc/', admin_storagelocation_regenerate_nfc, name='admin_storagelocation_regenerate_nfc'),
    path('storage-locations/<int:pk>/delete/', StorageLocationDeleteView.as_view(), name='admin_storagelocation_delete'),

    # Overviews (Dashboards)
    path('overview/', OverviewListView.as_view(), name='admin_overviews'),
    path('overview/add/', admin_overview_create, name='admin_overview_add'),
    path('overview/<int:pk>/edit/', admin_overview_edit, name='admin_overview_edit'),
    path('overview/<int:pk>/delete/', admin_overview_delete, name='admin_overview_delete'),

    # Feedback Quick-Action (Status setzen)
    path('feedback/<int:pk>/set-status/', admin_feedback_set_status, name='admin_feedback_set_status'),
]
