# Re-Export aller View-Klassen für urls.py-Kompatibilität
# urls.py importiert weiterhin aus inventory.views.*

from .dashboard import (
    OverviewDashboardView,
    DashboardSelectorView,
    dashboards,
    ToggleFavoriteView,
    ToggleOverviewFavoriteView,
)
from .items import (
    AddEquipmentItem,
    AddConsumableItem,
    EditItem,
    DeleteItem,
    DeleteImageView,
    RegenerateQRView,
    RegenerateNFCTokenView,
    ItemHistoryRollbackView,
    MoveItemToOverviewView,
    BulkItemActionView,
)
from .overviews import (
    OverviewRequestForm,
    OverviewRequestCreateView,
    OverviewExportView,
    ScheduledExportView,
    ScheduledExportRunView,
    MovementReportView,
)
from .feedback import (
    FeedbackListView,
    FeedbackDetailView,
    FeedbackCreateView,
    FeedbackVoteView,
    FeedbackCommentCreateView,
)
from .item_api import (
    MarkItemAPI,
    QuickAdjustQuantityView,
    NFCItemRedirectView,
    NFCStorageLocationView,
    DrawerItemsAPI,
    QRCodeListAdminView,
    ItemAttachmentUploadView,
    ItemAttachmentDeleteView,
    ItemCommentCreateView,
)
from .borrowed import BorrowedItemsView, ReturnItemView
from .auth import (
    Index,
    SignUpView,
    CustomAuthForm,
    PatchNotesView,
    ScanBarcodeView,
    BarcodeListView,
)

# Alte Dashboard-Varianten + TestFormView – werden bewusst NICHT exportiert
# (TestFormView und DashboardLanding sind Legacy und werden in cleanup entfernt)

__all__ = [
    "OverviewDashboardView",
    "DashboardSelectorView",
    "dashboards",
    "ToggleFavoriteView",
    "ToggleOverviewFavoriteView",
    "AddEquipmentItem",
    "AddConsumableItem",
    "EditItem",
    "DeleteItem",
    "DeleteImageView",
    "RegenerateQRView",
    "RegenerateNFCTokenView",
    "ItemHistoryRollbackView",
    "MoveItemToOverviewView",
    "BulkItemActionView",
    "OverviewRequestForm",
    "OverviewRequestCreateView",
    "OverviewExportView",
    "ScheduledExportView",
    "ScheduledExportRunView",
    "MovementReportView",
    "FeedbackListView",
    "FeedbackDetailView",
    "FeedbackCreateView",
    "FeedbackVoteView",
    "FeedbackCommentCreateView",
    "MarkItemAPI",
    "QuickAdjustQuantityView",
    "NFCItemRedirectView",
    "NFCStorageLocationView",
    "DrawerItemsAPI",
    "QRCodeListAdminView",
    "ItemAttachmentUploadView",
    "ItemAttachmentDeleteView",
    "ItemCommentCreateView",
    "BorrowedItemsView",
    "ReturnItemView",
    "Index",
    "SignUpView",
    "CustomAuthForm",
    "PatchNotesView",
    "ScanBarcodeView",
    "BarcodeListView",
]
