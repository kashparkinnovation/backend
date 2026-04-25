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


class VendorApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('is_approved',)
