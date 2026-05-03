from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, MeView, ChangePasswordView,
    AdminUserViewSet, PublicContactLeadView, AdminContactLeadViewSet,
    AdminDelegateAccessView,
    OTPLoginView, OTPSignupView, OTPForgotPasswordView,
    EmailOTPLoginView, EmailOTPSignupView, EmailOTPForgotPasswordView,
    SendEmailOTPView, RegisterWithEmailOTPView,
    AdminUserToggleActiveView,
)

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
    path('users/<int:pk>/toggle-active/', AdminUserToggleActiveView.as_view(), name='toggle-user-active'),
    path('leads/', PublicContactLeadView.as_view(), name='public-leads'),
    path('otp/login/',           OTPLoginView.as_view(),           name='otp-login'),
    path('otp/register/',         OTPSignupView.as_view(),          name='otp-register'),
    path('otp/forgot-password/',  OTPForgotPasswordView.as_view(),  name='otp-forgot-password'),
    # Email magic-link OTP
    path('otp/email-login/',           EmailOTPLoginView.as_view(),          name='otp-email-login'),
    path('otp/email-register/',        EmailOTPSignupView.as_view(),         name='otp-email-register'),
    path('otp/email-forgot-password/', EmailOTPForgotPasswordView.as_view(), name='otp-email-forgot-password'),
    # Email 6-digit OTP for password-based signup
    path('email-otp/send/',     SendEmailOTPView.as_view(),         name='email-otp-send'),
    path('email-otp/register/', RegisterWithEmailOTPView.as_view(), name='email-otp-register'),
    path('', include(router.urls)),
]
