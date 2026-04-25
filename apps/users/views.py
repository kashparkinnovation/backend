from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, TokenResponseSerializer
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

    def get_queryset(self):
        return CustomUser.objects.filter(role=UserRole.ADMIN).order_by('-created_at')

    def perform_create(self, serializer):
        # We also need to map the standard fields like password
        user = serializer.save(role=UserRole.ADMIN, is_staff=True)
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.save()

    def perform_update(self, serializer):
        user = serializer.save()
        if 'password' in self.request.data and self.request.data['password']:
            user.set_password(self.request.data['password'])
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
