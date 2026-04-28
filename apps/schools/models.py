from django.db import models
from apps.vendors.models import Vendor
from django.conf import settings


class SchoolApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class School(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='schools', null=True, blank=True)
    # Optional dedicated school-staff account (role=school) that logs into the School Portal
    school_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='school_profile'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to='schools/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Approval workflow
    approval_status = models.CharField(
        max_length=20,
        choices=SchoolApprovalStatus.choices,
        default=SchoolApprovalStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'schools'

    def __str__(self):
        return f'{self.name} ({self.code})'

    @property
    def is_approved(self):
        return self.approval_status == SchoolApprovalStatus.APPROVED

    @property
    def is_pending(self):
        return self.approval_status == SchoolApprovalStatus.PENDING

    @property
    def is_rejected(self):
        return self.approval_status == SchoolApprovalStatus.REJECTED


class VendorChangeRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class VendorChangeRequest(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='vendor_change_requests')
    old_vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_vendor_requests')
    new_vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='new_vendor_requests')
    status = models.CharField(
        max_length=20,
        choices=VendorChangeRequestStatus.choices,
        default=VendorChangeRequestStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendor_change_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Change Vendor for {self.school.name} to {self.new_vendor.business_name} ({self.status})'
