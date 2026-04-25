"""
Admin-level platform-wide stats API.
"""
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.users.permissions import IsAdmin
from rest_framework import serializers
from apps.vendors.models import PlatformSettings

class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ['platform_commission_percent', 'updated_at']


class AdminPlatformSettingsView(APIView):
    """GET/PUT /api/v1/admin/settings/ — Manage platform settings."""
    permission_classes = [IsAdmin]

    def get(self, request):
        settings = PlatformSettings.get_settings()
        return Response(PlatformSettingsSerializer(settings).data)

    def put(self, request):
        settings = PlatformSettings.get_settings()
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminPlatformStatsView(APIView):
    """GET /api/v1/admin/stats/ — Real-time platform KPIs."""
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.schools.models import School, SchoolApprovalStatus
        from apps.vendors.models import Vendor
        from apps.students.models import StudentProfile
        from apps.orders.models import Order, OrderStatus
        from apps.users.models import CustomUser

        now = timezone.now()

        # ── Schools ──
        schools_approved = School.objects.filter(approval_status=SchoolApprovalStatus.APPROVED).count()
        schools_pending = School.objects.filter(approval_status=SchoolApprovalStatus.PENDING).count()
        schools_rejected = School.objects.filter(approval_status=SchoolApprovalStatus.REJECTED).count()

        # ── Vendors ──
        vendors_approved = Vendor.objects.filter(is_approved=True).count()
        vendors_pending = Vendor.objects.filter(is_approved=False).count()

        # ── Students ──
        students_total = StudentProfile.objects.count()
        students_verified = StudentProfile.objects.filter(is_verified=True).count()

        # ── Users ──
        total_users = CustomUser.objects.count()

        # ── Orders ──
        total_orders = Order.objects.count()
        orders_by_status = {}
        for s, label in OrderStatus.choices:
            count = Order.objects.filter(status=s).count()
            if count:
                orders_by_status[s] = count

        active_statuses = [OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
        total_revenue = float(
            Order.objects.filter(status__in=active_statuses)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue_this_month = float(
            Order.objects.filter(status__in=active_statuses, created_at__gte=month_start)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )

        # ── Monthly Revenue Trend (last 6 months) ──
        monthly_revenue = []
        for i in range(5, -1, -1):
            month_date = now.date().replace(day=1) - datetime.timedelta(days=i * 28)
            month_date = month_date.replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1)

            rev = float(
                Order.objects.filter(
                    created_at__date__gte=month_date,
                    created_at__date__lt=next_month,
                    status__in=active_statuses,
                ).aggregate(total=Sum('total_amount'))['total'] or 0
            )
            monthly_revenue.append({
                'month': month_date.strftime('%b %Y'),
                'revenue': rev,
            })

        return Response({
            'schools': {
                'approved': schools_approved,
                'pending': schools_pending,
                'rejected': schools_rejected,
                'total': schools_approved + schools_pending + schools_rejected,
            },
            'vendors': {
                'approved': vendors_approved,
                'pending': vendors_pending,
                'total': vendors_approved + vendors_pending,
            },
            'students': {
                'total': students_total,
                'verified': students_verified,
            },
            'users': {
                'total': total_users,
            },
            'orders': {
                'total': total_orders,
                'by_status': orders_by_status,
            },
            'revenue': {
                'total': total_revenue,
                'this_month': revenue_this_month,
            },
            'monthly_revenue': monthly_revenue,
        })
