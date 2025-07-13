from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  # Importiere auth_views richtig

urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('dashboard/', views.Dashboard.as_view(), name='dashboard'),
    path('add-item/', views.AddItem.as_view(), name='add-item'),
    path('edit-item/<int:pk>/', views.EditItem.as_view(), name='edit-item'),
    path('delete-item/<int:pk>/', views.DeleteItem.as_view(), name='delete-item'),
    path('signup/', views.SignUpView.as_view(), name='signup'),

    # Login und Logout URLs, inklusive Redirects nach erfolgreichem Login oder Logout
    path('login/', auth_views.LoginView.as_view(
        template_name='inventory/login.html',
        redirect_authenticated_user=True  # Nutzer wird nach Login weitergeleitet
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        template_name='inventory/logout.html'
    ), name='logout'),

    # Barcode-Verwaltung URLs
    path('barcodes/', views.BarcodeListView.as_view(), name='barcode-list'),
    path('scan-barcode/', views.ScanBarcodeView.as_view(), name='scan-barcode'),
]
