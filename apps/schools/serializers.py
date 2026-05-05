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
        # code is writable on creation so vendors can set their school identifier


class AdminSchoolCreateSerializer(serializers.ModelSerializer):
    school_email = serializers.EmailField(write_only=True)
    school_password = serializers.CharField(write_only=True)

    class Meta:
        model = School
        fields = (
            'name', 'code', 'address', 'city', 'state', 'pincode',
            'contact_email', 'contact_phone', 'logo',
            'school_email', 'school_password'
        )

    def create(self, validated_data):
        from apps.users.models import CustomUser, UserRole
        school_email = validated_data.pop('school_email')
        school_password = validated_data.pop('school_password')

        school_name = validated_data.get('name', '')

        # Create user account for the school staff
        user, created = CustomUser.objects.get_or_create(
            email=school_email,
            defaults={
                'first_name': school_name[:100],  # cap to field max_length
                'last_name': '',
                'role': UserRole.SCHOOL,
            }
        )
        if created or not user.has_usable_password():
            user.set_password(school_password)
            user.save()

        # Build School profile
        # Automatically approve schools created by Admin
        validated_data['school_user'] = user
        validated_data['approval_status'] = SchoolApprovalStatus.APPROVED
        validated_data['approved_at'] = timezone.now()

        school = School.objects.create(**validated_data)
        return school


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


from .models import VendorChangeRequest, VendorChangeRequestStatus

class VendorChangeRequestSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    new_vendor_name = serializers.CharField(source='new_vendor.business_name', read_only=True)
    old_vendor_name = serializers.CharField(source='old_vendor.business_name', read_only=True, allow_null=True)

    class Meta:
        model = VendorChangeRequest
        fields = (
            'id', 'school', 'school_name', 'old_vendor', 'old_vendor_name',
            'new_vendor', 'new_vendor_name', 'status', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'school', 'old_vendor', 'created_at', 'updated_at')
