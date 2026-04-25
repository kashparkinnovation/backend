from django.urls import path
from .views import (
    SchoolListCreateView, SchoolDetailView, SchoolApproveView,
    SchoolProfileView, SchoolDashboardView,
    PublicSchoolListView, PublicSchoolDetailView,
)

app_name = 'schools'

urlpatterns = [
    # Public (no auth) — for landing page / browse
    path('public/', PublicSchoolListView.as_view(), name='public-school-list'),
    path('public/<int:pk>/', PublicSchoolDetailView.as_view(), name='public-school-detail'),

    # School portal uses this to get/update its own data
    path('profile/', SchoolProfileView.as_view(), name='school-profile'),
    path('dashboard/', SchoolDashboardView.as_view(), name='school-dashboard'),
    
    path('', SchoolListCreateView.as_view(), name='school-list'),
    path('<int:pk>/', SchoolDetailView.as_view(), name='school-detail'),
    path('<int:pk>/approve/', SchoolApproveView.as_view(), name='school-approve'),
]
