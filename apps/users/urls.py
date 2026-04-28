from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, LogoutView, MeView, ChangePasswordView, AdminUserViewSet, PublicContactLeadView, AdminContactLeadViewSet, AdminDelegateAccessView, OTPLoginView, OTPSignupView, OTPForgotPasswordView

app_name = 'users'

router = DefaultRouter()
router.register(r'admins', AdminUserViewSet, basename='admins')
router.register(r'admin/leads', AdminContactLeadViewSet, basename='admin-leads')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('delegate-access/', AdminDelegateAccessView.as_view(), name='delegate-access'),
    path('leads/', PublicContactLeadView.as_view(), name='public-leads'),
    path('otp/login/', OTPLoginView.as_view(), name='otp-login'),
    path('otp/register/', OTPSignupView.as_view(), name='otp-register'),
    path('otp/forgot-password/', OTPForgotPasswordView.as_view(), name='otp-forgot-password'),
    path('', include(router.urls)),
]
