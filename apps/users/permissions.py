from rest_framework import permissions
from apps.users.models import UserRole


class IsAdmin(permissions.BasePermission):
    """Only Platform Admins."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsVendor(permissions.BasePermission):
    """Only Vendors."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.VENDOR


class IsSchool(permissions.BasePermission):
    """Only School staff."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.SCHOOL


class IsStudent(permissions.BasePermission):
    """Only Students/Parents."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.STUDENT


class IsAdminOrVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [UserRole.ADMIN, UserRole.VENDOR]


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN
