from django.urls import path
from .views import VendorProfileView, VendorDashboardView, VendorCustomerListView, VendorAnalyticsView, VendorLedgerView

app_name = 'vendors'

urlpatterns = [
    path('profile/',    VendorProfileView.as_view(),    name='vendor-profile'),
    path('dashboard/',  VendorDashboardView.as_view(),  name='vendor-dashboard'),
    path('customers/',  VendorCustomerListView.as_view(), name='vendor-customers'),
    path('analytics/',  VendorAnalyticsView.as_view(),  name='vendor-analytics'),
    path('ledger/',     VendorLedgerView.as_view(),     name='vendor-ledger'),
]
