import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, TokenResponseSerializer,
    OTPLoginSerializer, OTPSignupSerializer, OTPForgotPasswordSerializer,
    EmailOTPLoginSerializer, EmailOTPSignupSerializer, EmailOTPForgotPasswordSerializer,
)
from .models import CustomUser


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — Create new user account."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/v1/auth/login/ — Authenticate and get JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — Blacklist refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/ — View / update own profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ — Change own password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'detail': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.raw_password = new_password
        user.save()
        return Response({'detail': 'Password changed successfully.'})

from rest_framework import viewsets
from .permissions import IsAdmin
from .models import UserRole

class AdminUserViewSet(viewsets.ModelViewSet):
    """
    GET/POST/PUT/DELETE /api/v1/auth/admins/ — Manage sub-admins.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    search_fields = ['first_name', 'last_name', 'email']

    def get_queryset(self):
        return CustomUser.objects.filter(role=UserRole.ADMIN).order_by('-created_at')

    def perform_create(self, serializer):
        # We also need to map the standard fields like password
        user = serializer.save(role=UserRole.ADMIN, is_staff=True)
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.raw_password = self.request.data['password']
            user.save()

    def perform_update(self, serializer):
        user = serializer.save()
        if 'password' in self.request.data and self.request.data['password']:
            user.set_password(self.request.data['password'])
            user.raw_password = self.request.data['password']
            user.save()

from .models import ContactLead
from .serializers import ContactLeadSerializer

class PublicContactLeadView(generics.CreateAPIView):
    """
    POST /api/v1/leads/ — Public endpoint for submitting contact forms.
    """
    serializer_class = ContactLeadSerializer
    permission_classes = [permissions.AllowAny]


class AdminContactLeadViewSet(viewsets.ModelViewSet):
    """
    GET/PUT/DELETE /api/v1/admin/leads/ — Manage inbound leads.
    """
    queryset = ContactLead.objects.all().order_by('-created_at')
    serializer_class = ContactLeadSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

from django.shortcuts import get_object_or_404

class AdminDelegateAccessView(APIView):
    """
    POST /api/v1/auth/delegate-access/ — Admin gets a JWT for a target user.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        target_user_id = request.data.get('user_id')
        if not target_user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(CustomUser, id=target_user_id)
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)


class AdminUserToggleActiveView(APIView):
    """PATCH /api/v1/auth/users/{id}/toggle-active/ — Admin toggles user is_active flag."""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        user = get_object_or_404(CustomUser, id=pk)
        if user == request.user:
            return Response({'detail': 'Cannot deactivate yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'id': user.id, 'is_active': user.is_active})


class OTPLoginView(APIView):
    """POST /api/v1/auth/otp/login/ — Login with Firebase Phone OTP token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)


class OTPSignupView(generics.CreateAPIView):
    """POST /api/v1/auth/otp/register/ — Register with Firebase Phone OTP token."""
    serializer_class = OTPSignupSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)


class OTPForgotPasswordView(APIView):
    """POST /api/v1/auth/otp/forgot-password/ — Reset password using Firebase OTP verification."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Reset password
        password = serializer.validated_data['password']
        user.set_password(password)
        user.raw_password = password
        user.save()
        
        return Response({'detail': 'Password reset successfully.'}, status=status.HTTP_200_OK)


# ─── Email magic-link OTP views ──────────────────────────────────────────

class EmailOTPLoginView(APIView):
    """POST /api/v1/auth/otp/email-login/ — Login via Firebase email sign-in link."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailOTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)


class EmailOTPSignupView(generics.CreateAPIView):
    """POST /api/v1/auth/otp/email-register/ — Register via Firebase email sign-in link."""
    serializer_class = EmailOTPSignupSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)


class EmailOTPForgotPasswordView(APIView):
    """POST /api/v1/auth/otp/email-forgot-password/ — Reset password via email sign-in link."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailOTPForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        new_password = serializer.validated_data['password']
        user.set_password(new_password)
        user.raw_password = new_password
        user.save()
        return Response({'detail': 'Password reset successfully.'}, status=status.HTTP_200_OK)


# ─── Email OTP (6-digit code) for password-based signup ────────────────────────

def _otp_cache_key(email: str) -> str:
    return f'signup_email_otp_{email.lower().strip()}'


class SendEmailOTPView(APIView):
    """
    POST /api/v1/auth/email-otp/send/
    Generates a 6-digit OTP, caches it (10 min), and emails it to the user.
    Body: { "email": "user@example.com" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'email': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {'email': 'An account with this email already exists. Please log in.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = str(random.randint(100000, 999999))
        cache.set(_otp_cache_key(email), otp, timeout=600)  # 10 minutes

        try:
            send_mail(
                subject='eSchoolKart — Email Verification OTP',
                message=(
                    f'Your eSchoolKart verification code is: {otp}\n\n'
                    'This code is valid for 10 minutes. Do not share it with anyone.'
                ),
                html_message=(
                    f'<div style="font-family:sans-serif;max-width:480px;margin:auto;">'
                    f'<h2 style="color:#4f46e5;">eSchoolKart</h2>'
                    f'<p>Your email verification code is:</p>'
                    f'<div style="font-size:2.5rem;font-weight:700;letter-spacing:0.5rem;'
                    f'color:#1e1b4b;margin:1rem 0;">{otp}</div>'
                    f'<p style="color:#6b7280;font-size:0.875rem;">'
                    f'Valid for 10 minutes. Do not share this code.</p></div>'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {'detail': f'Failed to send email: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'detail': 'OTP sent successfully.'}, status=status.HTTP_200_OK)


class RegisterWithEmailOTPView(APIView):
    """
    POST /api/v1/auth/email-otp/register/
    Verifies the 6-digit OTP then creates the student account.
    Body: { email, first_name, last_name, password, email_otp }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email    = request.data.get('email', '').strip().lower()
        otp      = str(request.data.get('email_otp', '')).strip()
        password = request.data.get('password', '')
        first_name = request.data.get('first_name', '').strip()
        last_name  = request.data.get('last_name', '').strip()

        # Validate required fields
        errors = {}
        if not email:      errors['email']      = 'Required.'
        if not otp:        errors['email_otp']  = 'Required.'
        if not password:   errors['password']   = 'Required.'
        if not first_name: errors['first_name'] = 'Required.'
        if not last_name:  errors['last_name']  = 'Required.'
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Verify OTP
        key = _otp_cache_key(email)
        stored_otp = cache.get(key)
        if not stored_otp:
            return Response(
                {'email_otp': 'OTP expired or not found. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if stored_otp != otp:
            return Response(
                {'email_otp': 'Incorrect OTP. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache.delete(key)  # consume OTP

        # Check duplicate
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {'email': 'An account with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user
        user = CustomUser.objects.create_user(
            email=email, password=password,
            first_name=first_name, last_name=last_name,
            role='student', is_active=True,
        )

        tokens = TokenResponseSerializer.get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)
