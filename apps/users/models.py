"""
Custom User model with email-based auth and role fields.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Platform Admin'
    VENDOR = 'vendor', 'Vendor'
    SCHOOL = 'school', 'School'
    STUDENT = 'student', 'Student/Parent'


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Granular RBAC Permissions for Sub-Admins
    can_manage_vendors = models.BooleanField(default=True)
    can_manage_schools = models.BooleanField(default=True)
    can_manage_students = models.BooleanField(default=True)
    can_manage_content = models.BooleanField(default=True)
    can_manage_reports = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class ContactLead(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    user_type = models.CharField(max_length=100)
    message = models.TextField()
    status = models.CharField(max_length=20, default='New')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_leads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.status})'
