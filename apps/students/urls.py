from django.urls import path
from .views import (
    StudentProfileListCreateView,
    StudentProfileDetailView,
    StudentVerifyView,
    StudentUnverifyView,
    VerificationRequestCreateView,
    SchoolVerificationQueueView,
    SchoolVerificationActionView,
    StudentCSVImportView,
    AdminVerificationQueueView,
    AdminVerificationActionView,
)

app_name = 'students'

urlpatterns = [
    # Student self-management
    path('', StudentProfileListCreateView.as_view(), name='profile-list'),
    path('<int:pk>/', StudentProfileDetailView.as_view(), name='profile-detail'),
    path('<int:pk>/verify/', StudentVerifyView.as_view(), name='direct-verify'),
    path('<int:pk>/unverify/', StudentUnverifyView.as_view(), name='unverify'),

    # Student submits a verification request
    path('verify-request/', VerificationRequestCreateView.as_view(), name='verify-request-create'),

    # School-facing
    path('school/verification-requests/', SchoolVerificationQueueView.as_view(), name='school-verify-queue'),
    path('school/verification-requests/<int:pk>/action/', SchoolVerificationActionView.as_view(), name='school-verify-action'),
    path('school/import/', StudentCSVImportView.as_view(), name='school-import'),
    
    # Admin-facing
    path('admin/verification-requests/', AdminVerificationQueueView.as_view(), name='admin-verify-queue'),
    path('admin/verification-requests/<int:pk>/action/', AdminVerificationActionView.as_view(), name='admin-verify-action'),
]
