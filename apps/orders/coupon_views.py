"""
Coupon management views for vendors.
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, SerializerMethodField, CharField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Coupon, DiscountType
from apps.users.permissions import IsVendor


class CouponSerializer(ModelSerializer):
    is_expired    = SerializerMethodField()
    is_exhausted  = SerializerMethodField()
    school_names  = SerializerMethodField()

    class Meta:
        model  = Coupon
        fields = (
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount', 'max_uses', 'used_count',
            'valid_from', 'valid_until', 'is_active',
            'schools', 'school_names',
            'is_expired', 'is_exhausted',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'used_count', 'created_at', 'updated_at')

    def get_is_expired(self, obj):
        return obj.is_expired

    def get_is_exhausted(self, obj):
        return obj.is_exhausted

    def get_school_names(self, obj):
        return [s.name for s in obj.schools.all()]


class CouponListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/orders/coupons/ — Vendor lists own coupons.
    POST /api/v1/orders/coupons/ — Vendor creates a coupon.
    """
    serializer_class   = CouponSerializer
    permission_classes = [IsVendor]

    def get_queryset(self):
        return Coupon.objects.filter(vendor=self.request.user.vendor_profile).prefetch_related('schools')

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor_profile)


class CouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/v1/orders/coupons/<pk>/
    """
    serializer_class   = CouponSerializer
    permission_classes = [IsVendor]

    def get_queryset(self):
        return Coupon.objects.filter(vendor=self.request.user.vendor_profile)


class CouponToggleView(APIView):
    """PATCH /api/v1/orders/coupons/<pk>/toggle/ — Toggle active status."""
    permission_classes = [IsVendor]

    def patch(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk, vendor=request.user.vendor_profile)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=['is_active'])
        return Response(CouponSerializer(coupon).data)
