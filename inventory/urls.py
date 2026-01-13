# inventory/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import CustomAuthForm
# API-Views
from .api import FeedbackSummaryAPI, HAStatusAPI

urlpatterns = [
    # 1) Frontend-Views
    path('', views.Index.as_view(), name='index'),
    path('dashboard/equipment/', views.EquipmentDashboardView.as_view(), name='dashboard-equipment'),
    path('dashboard/verbrauch/', views.ConsumableDashboardView.as_view(), name='dashboard-consumables'),

    path('add-equipment/', views.AddEquipmentItem.as_view(), name='add-equipment'),
    path('add-verbrauch/', views.AddConsumableItem.as_view(), name='add-consumables'),
    path('add-consumable/', views.AddConsumableItem.as_view(), name='add-consumable'),

    path('edit-item/<int:pk>/', views.EditItem.as_view(), name='edit-item'),
    path('delete-item/<int:pk>/', views.DeleteItem.as_view(), name='delete-item'),

    path('edit-item/<int:pk>/regenerate-qr/', views.RegenerateQRView.as_view(), name='regenerate-qr'),
    path('edit-item/<int:pk>/delete-image/', views.DeleteImageView.as_view(), name='delete-image'),
    path('item/<int:item_id>/mark/', views.MarkItemAPI.as_view(), name='mark-item'),

    # Auth
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="inventory/login.html",
            authentication_form=CustomAuthForm,
        ),
        name="login",
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Barcode
    path('barcodes/', views.BarcodeListView.as_view(), name='barcode-list'),
    path('scan-barcode/', views.ScanBarcodeView.as_view(), name='scan-barcode'),

    # Verleih
    path('borrow/<int:item_id>/', views.BorrowedItemsView.as_view(), name='borrow-item'),
    path('return/<int:borrow_id>/', views.ReturnItemView.as_view(), name='return-item'),

    # 2) Eigenes Admin-Frontend
    path('manage/', include('inventory.admin_urls')),

    # 3) Modulares Dashboard (Overview)
    path('dashboards/', views.DashboardSelectorView.as_view(), name='dashboards'),
    path('dashboards/<slug:slug>/', views.OverviewDashboardView.as_view(), name='overview-dashboard'),

    # 4) Feedback
    path('feedback/', views.FeedbackListView.as_view(), name='feedback-list'),
    path('feedback/add/', views.FeedbackCreateView.as_view(), name='feedback-add'),
    path('feedback/<int:pk>/', views.FeedbackDetailView.as_view(), name='feedback-detail'),
    path('feedback/<int:pk>/vote/', views.FeedbackVoteView.as_view(), name='feedback-vote'),
    path('feedback/<int:pk>/comment/', views.FeedbackCommentCreateView.as_view(), name='feedback-comment'),

    # 5) API für Home Assistant Dashboard
    path('api/feedback/summary/', FeedbackSummaryAPI.as_view(), name='feedback-summary'),

    # 6) Health / HA-Status
    path('api/health/ha/', HAStatusAPI.as_view(), name='ha-health'),

    path("item/<int:pk>/move/",views.MoveItemToOverviewView.as_view(),name="move-item-to-overview",),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
