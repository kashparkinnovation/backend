from django.urls import path
from .views import AdminVendorListView, AdminVendorDetailView, AdminVendorApproveView, AdminVendorCreateView
from .admin_views import AdminPlatformStatsView, AdminPlatformSettingsView

app_name = 'admin-vendors'

urlpatterns = [
    path('settings/', AdminPlatformSettingsView.as_view(), name='platform-settings'),
    path('stats/', AdminPlatformStatsView.as_view(), name='platform-stats'),
    path('vendors/', AdminVendorListView.as_view(), name='vendor-list'),
    path('vendors/admin-create/', AdminVendorCreateView.as_view(), name='admin-vendor-create'),
    path('vendors/<int:pk>/', AdminVendorDetailView.as_view(), name='vendor-detail'),
    path('vendors/<int:pk>/approve/', AdminVendorApproveView.as_view(), name='vendor-approve'),
]
