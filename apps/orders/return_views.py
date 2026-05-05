"""
Return/Exchange request views.
"""
from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ReturnRequest, ReturnRequestStatus, ReturnRequestType, Order, OrderStatus
from apps.users.permissions import IsVendor, IsStudent
from rest_framework.permissions import IsAuthenticated


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    student_name = serializers.CharField(source='order.student_profile.student_name', read_only=True)
    school_name = serializers.CharField(source='order.school.name', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)

    class Meta:
        model = ReturnRequest
        fields = (
            'id', 'order', 'order_number', 'student_name', 'school_name',
            'request_type', 'reason', 'status',
            'exchange_size', 'exchange_color',
            'admin_notes', 'reviewed_by_email', 'reviewed_at',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'status', 'admin_notes', 'reviewed_by_email', 'reviewed_at', 'created_at', 'updated_at')


class ReturnRequestCreateSerializer(serializers.Serializer):
    request_type = serializers.ChoiceField(choices=ReturnRequestType.choices)
    reason = serializers.CharField()
    exchange_size = serializers.CharField(required=False, allow_blank=True, default='')
    exchange_color = serializers.CharField(required=False, allow_blank=True, default='')


class ReturnRequestActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'complete'])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default='')


# ─── Student creates a return request ─────────────────────────────────────────

class ReturnRequestCreateView(APIView):
    """POST /api/v1/orders/{pk}/return/ — Student or School creates a return/exchange request."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if user.role == 'student':
            order = get_object_or_404(Order, pk=pk, student_profile__parent=user)
        elif user.role == 'school':
            school = getattr(user, 'school_profile', None)
            order = get_object_or_404(Order, pk=pk, school=school)
        else:
            return Response({'detail': 'Not authorized.'}, status=403)

        # Only distributed orders can be returned/exchanged
        if order.status != OrderStatus.DISTRIBUTED:
            return Response({'detail': 'Return/exchange requests can only be raised after the order has been distributed.'}, status=400)

        # Prevent duplicate pending requests
        if ReturnRequest.objects.filter(order=order, status=ReturnRequestStatus.PENDING).exists():
            return Response({'detail': 'A pending return request already exists for this order.'}, status=400)

        serializer = ReturnRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        rr = ReturnRequest.objects.create(
            order=order,
            request_type=data['request_type'],
            reason=data['reason'],
            exchange_size=data.get('exchange_size', ''),
            exchange_color=data.get('exchange_color', ''),
        )
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_201_CREATED)


# ─── Student lists own return requests ─────────────────────────────────────────

class StudentReturnRequestListView(generics.ListAPIView):
    """GET /api/v1/orders/returns/ — Student sees their own return requests."""
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return ReturnRequest.objects.filter(
                order__student_profile__parent=user
            ).select_related('order', 'order__student_profile', 'order__school', 'reviewed_by')
        elif user.role == 'school':
            return ReturnRequest.objects.filter(
                order__school=getattr(user, 'school_profile', None)
            ).select_related('order', 'order__student_profile', 'order__school', 'reviewed_by')
        elif user.role == 'vendor':
            return ReturnRequest.objects.filter(
                order__vendor__user=user
            ).select_related('order', 'order__student_profile', 'order__school', 'reviewed_by')
        return ReturnRequest.objects.none()


# ─── Vendor reviews return request ─────────────────────────────────────────────

class ReturnRequestActionView(APIView):
    """PATCH /api/v1/orders/returns/{pk}/ — Vendor approves/rejects/completes a return."""
    permission_classes = [IsVendor]

    def patch(self, request, pk):
        rr = get_object_or_404(ReturnRequest, pk=pk, order__vendor__user=request.user)

        serializer = ReturnRequestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action_map = {
            'approve': ReturnRequestStatus.APPROVED,
            'reject': ReturnRequestStatus.REJECTED,
            'complete': ReturnRequestStatus.COMPLETED,
        }
        rr.status = action_map[data['action']]
        rr.admin_notes = data.get('admin_notes', '')
        rr.reviewed_by = request.user
        rr.reviewed_at = timezone.now()
        rr.save()

        # If completed and it's a return, mark the order as refunded
        if rr.status == ReturnRequestStatus.COMPLETED and rr.request_type == ReturnRequestType.RETURN:
            rr.order.status = OrderStatus.REFUNDED
            rr.order.save(update_fields=['status'])

        return Response(ReturnRequestSerializer(rr).data)
