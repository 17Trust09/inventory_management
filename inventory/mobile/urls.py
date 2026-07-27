from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path
from inventory import views
from inventory.views import CustomAuthForm
from inventory.api import FeedbackSummaryAPI, HAStatusAPI, SystemHealthAPI, MarkedItemsAPI, QuickAddCategoryAPI, QuickAddTagAPI, QuickAddStorageLocationAPI, SimilarItemsAPI
from inventory.admin_urls import urlpatterns as admin_urlpatterns
from inventory.mobile import views as mobile_views


urlpatterns = [
    path("settings/", mobile_views.MobileSettingsView.as_view(), name="mobile-settings"),
    path("categories/", mobile_views.MobileCategoryListView.as_view(), name="mobile-categories"),
    path("categories/add/", mobile_views.MobileCategoryCreateView.as_view(), name="mobile-category-add"),
    path("categories/<int:pk>/edit/", mobile_views.MobileCategoryUpdateView.as_view(), name="mobile-category-edit"),
    path("categories/<int:pk>/delete/", mobile_views.MobileCategoryDeleteView.as_view(), name="mobile-category-delete"),
    path("tags/", mobile_views.MobileTagListView.as_view(), name="mobile-tags"),
    path("tags/add/", mobile_views.MobileTagCreateView.as_view(), name="mobile-tag-add"),
    path("tags/<int:pk>/edit/", mobile_views.MobileTagUpdateView.as_view(), name="mobile-tag-edit"),
    path("tags/<int:pk>/delete/", mobile_views.MobileTagDeleteView.as_view(), name="mobile-tag-delete"),
    path("locations/", mobile_views.MobileLocationListView.as_view(), name="mobile-locations"),
    path("locations/add/", mobile_views.MobileLocationCreateView.as_view(), name="mobile-location-add"),
    path("locations/<int:pk>/edit/", mobile_views.MobileLocationUpdateView.as_view(), name="mobile-location-edit"),
    path("locations/<int:pk>/delete/", mobile_views.MobileLocationDeleteView.as_view(), name="mobile-location-delete"),
    path("search/", mobile_views.MobileSearchView.as_view(), name="mobile-search"),
    path("scan/", mobile_views.MobileScanView.as_view(), name="mobile-scan"),
    path("quick-add/", mobile_views.MobileAddEquipmentItem.as_view(), name="mobile-quick-add"),
    path("", views.Index.as_view(), name="mobile-index"),
    path("add-equipment/", mobile_views.MobileAddEquipmentItem.as_view(), name="mobile-add-equipment"),
    path("add-verbrauch/", mobile_views.MobileAddConsumableItem.as_view(), name="mobile-add-consumables"),
    path("add-consumable/", mobile_views.MobileAddConsumableItem.as_view(), name="mobile-add-consumable"),
    path("edit-item/<int:pk>/", mobile_views.MobileEditItem.as_view(), name="mobile-edit-item"),
    path("delete-item/<int:pk>/", views.DeleteItem.as_view(), name="mobile-delete-item"),
    path("edit-item/<int:pk>/regenerate-qr/", views.RegenerateQRView.as_view(), name="mobile-regenerate-qr"),
    path("edit-item/<int:pk>/regenerate-nfc/", views.RegenerateNFCTokenView.as_view(), name="mobile-regenerate-nfc"),
    path("edit-item/<int:pk>/delete-image/", views.DeleteImageView.as_view(), name="mobile-delete-image"),
    path("item/<int:pk>/history/<int:history_id>/rollback/", views.ItemHistoryRollbackView.as_view(), name="mobile-item-history-rollback"),
    path("item/<int:item_id>/mark/", views.MarkItemAPI.as_view(), name="mobile-mark-item"),
    path("item/<int:item_id>/favorite/", views.ToggleFavoriteView.as_view(), name="mobile-toggle-favorite"),
    path("item/<int:item_id>/attachments/", views.ItemAttachmentUploadView.as_view(), name="mobile-item-attachment-upload"),
    path("item/attachments/<int:attachment_id>/delete/", views.ItemAttachmentDeleteView.as_view(), name="mobile-item-attachment-delete"),
    path("items/bulk-action/", views.BulkItemActionView.as_view(), name="mobile-bulk-item-action"),
    path("item/<int:item_id>/adjust-quantity/", views.QuickAdjustQuantityView.as_view(), name="mobile-adjust-quantity"),
    path("item/<int:item_id>/comment/", views.ItemCommentCreateView.as_view(), name="mobile-item-comment-add"),
    path("nfc/<str:token>/", views.NFCItemRedirectView.as_view(), name="mobile-nfc-redirect"),
    path("nfc/location/<str:token>/", views.NFCStorageLocationView.as_view(), name="mobile-nfc-location-redirect"),
    path("signup/", views.SignUpView.as_view(), name="mobile-signup"),
    path("login/", auth_views.LoginView.as_view(template_name="inventory/login.html", authentication_form=CustomAuthForm), name="mobile-login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="mobile-login"), name="mobile-logout"),
    path("barcodes/", views.BarcodeListView.as_view(), name="mobile-barcode-list"),
    path("scan-barcode/", views.ScanBarcodeView.as_view(), name="mobile-scan-barcode"),
    path("patch-notes/", views.PatchNotesView.as_view(), name="mobile-patch-notes"),
    path("borrow/<int:item_id>/", views.BorrowedItemsView.as_view(), name="mobile-borrow-item"),
    path("return/<int:borrow_id>/", views.ReturnItemView.as_view(), name="mobile-return-item"),
    path("dashboards/", views.DashboardSelectorView.as_view(template_name="mobile/dashboard.html"), name="mobile-dashboards"),
    path("overview/add/", views.OverviewRequestCreateView.as_view(), name="mobile-overview-request-add"),
    path("dashboards/<slug:slug>/", views.OverviewDashboardView.as_view(template_name="mobile/overview_dashboard.html"), name="mobile-overview-dashboard"),
    path("dashboards/<slug:slug>/favorite/", views.ToggleOverviewFavoriteView.as_view(), name="mobile-overview-favorite"),
    path("dashboards/<slug:slug>/export/pdf/", views.OverviewExportView.as_view(), {"export_format": "pdf"}, name="mobile-overview-export-pdf"),
    path("dashboards/<slug:slug>/export/<str:export_format>/", views.OverviewExportView.as_view(), name="mobile-overview-export"),
    path("exports/scheduled/", views.ScheduledExportView.as_view(), name="mobile-scheduled-exports"),
    path("exports/scheduled/<int:pk>/run/", views.ScheduledExportRunView.as_view(), name="mobile-scheduled-export-run"),
    path("reports/movements/", views.MovementReportView.as_view(), name="mobile-movement-report"),
    path("feedback/", views.FeedbackListView.as_view(), name="mobile-feedback-list"),
    path("feedback/add/", views.FeedbackCreateView.as_view(), name="mobile-feedback-add"),
    path("feedback/<int:pk>/", views.FeedbackDetailView.as_view(), name="mobile-feedback-detail"),
    path("feedback/<int:pk>/vote/", views.FeedbackVoteView.as_view(), name="mobile-feedback-vote"),
    path("feedback/<int:pk>/comment/", views.FeedbackCommentCreateView.as_view(), name="mobile-feedback-comment"),
    path("api/feedback/summary/", FeedbackSummaryAPI.as_view(), name="mobile-feedback-summary"),
    path("api/health/ha/", HAStatusAPI.as_view(), name="mobile-ha-health"),
    path("api/health/system/", SystemHealthAPI.as_view(), name="mobile-system-health"),
    path("api/marked-items/", MarkedItemsAPI.as_view(), name="mobile-marked-items"),
    path("api/categories/quick-add/", QuickAddCategoryAPI.as_view(), name="mobile-api-quick-add-category"),
    path("api/tags/quick-add/", QuickAddTagAPI.as_view(), name="mobile-api-quick-add-tag"),
    path("api/storage-locations/quick-add/", QuickAddStorageLocationAPI.as_view(), name="mobile-api-quick-add-storage-location"),
    path("api/items/similar/", SimilarItemsAPI.as_view(), name="mobile-api-similar-items"),
    path("item/<int:pk>/move/", views.MoveItemToOverviewView.as_view(), name="mobile-move-item-to-overview"),
]

urlpatterns += [path(f"manage/{pattern.pattern}", pattern.callback, pattern.default_args, name=f"mobile-{pattern.name}") for pattern in admin_urlpatterns]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
