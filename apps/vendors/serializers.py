from rest_framework import serializers
from .models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Vendor
        fields = (
            'id', 'user', 'user_email', 'user_name',
            'business_name', 'gst_number', 'address', 'city', 'state', 'pincode',
            'logo', 'is_approved', 'approved_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'is_approved', 'approved_at', 'created_at', 'updated_at')


class AdminVendorCreateSerializer(serializers.ModelSerializer):
    vendor_email = serializers.EmailField(write_only=True)
    vendor_password = serializers.CharField(write_only=True)
    school_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Vendor
        fields = (
            'business_name', 'gst_number', 'address', 'city', 'state', 'pincode', 'logo',
            'vendor_email', 'vendor_password', 'school_id'
        )

    def create(self, validated_data):
        from apps.users.models import CustomUser, UserRole
        from apps.schools.models import School
        from django.utils import timezone

        vendor_email = validated_data.pop('vendor_email')
        vendor_password = validated_data.pop('vendor_password')
        school_id = validated_data.pop('school_id')

        # Create/Get vendor user profile
        user, created = CustomUser.objects.get_or_create(
            email=vendor_email,
            defaults={
                'first_name': validated_data.get('business_name'),
                'role': UserRole.VENDOR
            }
        )
        if created or not user.has_usable_password():
            user.set_password(vendor_password)
            user.save()

        # Build Vendor profile
        validated_data['user'] = user
        # Let's auto-approve vendors created by admin
        validated_data['is_approved'] = True
        validated_data['approved_at'] = timezone.now()

        vendor = Vendor.objects.create(**validated_data)

        # Attach to the Target School (replaces any active vendor)
        School.objects.filter(id=school_id).update(vendor=vendor)

        return vendor


class VendorApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('is_approved',)
