from django.urls import path
from . import views
from . import admin_views
from django.contrib.auth import views as auth_views
from .admin_views import admin_qr_codes_view

urlpatterns = [
    # Startseite
    path('', views.Index.as_view(), name='index'),

    # Dashboard + CRUD
    path('dashboard/', views.Dashboard.as_view(), name='dashboard'),
    path('add-item/', views.AddItem.as_view(), name='add-item'),
    path('edit-item/<int:pk>/', views.EditItem.as_view(), name='edit-item'),
    path('delete-item/<int:pk>/', views.DeleteItem.as_view(), name='delete-item'),

    # ➕ Zusatzfunktionen im Bearbeitungsmenü
    path('edit-item/<int:pk>/regenerate-qr/', views.RegenerateQRView.as_view(), name='regenerate-qr'),
    path('edit-item/<int:pk>/delete-image/', views.DeleteImageView.as_view(), name='delete-image'),

    # Registrierung
    path('signup/', views.SignUpView.as_view(), name='signup'),

    # Authentifizierung
    path('login/', auth_views.LoginView.as_view(
        template_name='inventory/login.html',
        redirect_authenticated_user=True
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        next_page='login'  # Nach Logout zur Login-Seite
    ), name='logout'),

    # Barcode
    path('barcodes/', views.BarcodeListView.as_view(), name='barcode-list'),
    path('scan-barcode/', views.ScanBarcodeView.as_view(), name='scan-barcode'),

    # 📄 Admin-Spezialseite: QR-Code-Übersicht
    path('admin-qr-codes/', admin_views.admin_qr_codes_view, name='admin-qr-codes'),

    path('testform/', views.TestFormView.as_view(), name='test-form'),
]
