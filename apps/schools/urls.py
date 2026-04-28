from django.urls import path
from .views import (
    SchoolListCreateView, SchoolDetailView, SchoolApproveView,
    SchoolProfileView, SchoolDashboardView,
    PublicSchoolListView, PublicSchoolDetailView,
    AdminSchoolCreateView,
    AdminRequestVendorChangeView, SchoolVendorChangeRequestView, SchoolVendorChangeApprovalView,
)

app_name = 'schools'

urlpatterns = [
    # Public (no auth) — for landing page / browse
    path('public/', PublicSchoolListView.as_view(), name='public-school-list'),
    path('public/<int:pk>/', PublicSchoolDetailView.as_view(), name='public-school-detail'),

    # School portal uses this to get/update its own data
    path('profile/', SchoolProfileView.as_view(), name='school-profile'),
    path('dashboard/', SchoolDashboardView.as_view(), name='school-dashboard'),
    
    path('vendor-change-requests/', SchoolVendorChangeRequestView.as_view(), name='school-vendor-change-requests'),
    path('vendor-change-requests/<int:pk>/approve/', SchoolVendorChangeApprovalView.as_view(), name='school-vendor-change-approve'),

    path('', SchoolListCreateView.as_view(), name='school-list'),
    path('admin-create/', AdminSchoolCreateView.as_view(), name='admin-school-create'),
    path('<int:pk>/', SchoolDetailView.as_view(), name='school-detail'),
    path('<int:pk>/approve/', SchoolApproveView.as_view(), name='school-approve'),
    path('<int:pk>/request-vendor-change/', AdminRequestVendorChangeView.as_view(), name='admin-request-vendor-change'),
]
