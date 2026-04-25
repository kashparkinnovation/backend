from rest_framework import serializers
from .models import School, SchoolApprovalStatus
from django.utils import timezone


class SchoolSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    is_approved = serializers.BooleanField(read_only=True)

    class Meta:
        model = School
        fields = (
            'id', 'vendor', 'vendor_name', 'name', 'code', 'address',
            'city', 'state', 'pincode', 'contact_email', 'contact_phone',
            'logo', 'is_active', 'approval_status', 'rejection_reason',
            'applied_at', 'approved_at', 'is_approved', 'school_user',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'vendor', 'approval_status', 'rejection_reason',
            'applied_at', 'approved_at', 'is_approved', 'school_user', 'created_at', 'updated_at',
        )


class SchoolCreateSerializer(serializers.ModelSerializer):
    """Vendor creates/updates a school application."""

    class Meta:
        model = School
        fields = (
            'name', 'code', 'address', 'city', 'state', 'pincode',
            'contact_email', 'contact_phone', 'logo',
        )
        read_only_fields = ('code',)


class SchoolApprovalSerializer(serializers.ModelSerializer):
    """Admin approves or rejects a school application."""
    approval_status = serializers.ChoiceField(choices=SchoolApprovalStatus.choices)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = School
        fields = ('approval_status', 'rejection_reason')

    def update(self, instance, validated_data):
        status = validated_data.get('approval_status')
        instance.approval_status = status
        instance.rejection_reason = validated_data.get('rejection_reason', '')
        if status == SchoolApprovalStatus.APPROVED:
            instance.approved_at = timezone.now()
        else:
            instance.approved_at = None
        instance.save()
        return instance
