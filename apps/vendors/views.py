from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from .models import Vendor
from .serializers import VendorSerializer, VendorApprovalSerializer, AdminVendorCreateSerializer
from apps.users.permissions import IsAdmin, IsVendor


class VendorProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/vendors/profile/ — Vendor views/updates own profile."""
    serializer_class = VendorSerializer
    permission_classes = [IsVendor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user.vendor_profile



class VendorDashboardView(APIView):
    """GET /api/v1/vendors/dashboard/ — Stats for the vendor's dashboard."""
    permission_classes = [IsVendor]

    def get(self, request):
        vendor = request.user.vendor_profile

        from apps.schools.models import School, SchoolApprovalStatus
        from apps.products.models import Product, ProductInventory
        from apps.orders.models import Order, OrderStatus

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        schools_count = School.objects.filter(
            vendor=vendor,
            approval_status=SchoolApprovalStatus.APPROVED,
        ).count()

        pending_schools = School.objects.filter(
            vendor=vendor,
            approval_status=SchoolApprovalStatus.PENDING,
        ).count()

        products_count = Product.objects.filter(vendor=vendor, is_active=True).count()

        total_variants = ProductInventory.objects.filter(product__vendor=vendor).count()

        low_stock_count = ProductInventory.objects.filter(
            product__vendor=vendor,
            quantity__lte=5,
            quantity__gt=0,
        ).count()

        out_of_stock_count = ProductInventory.objects.filter(
            product__vendor=vendor,
            quantity=0,
        ).count()

        pending_orders = Order.objects.filter(
            vendor=vendor,
            status=OrderStatus.PENDING,
        ).count()

        processing_orders = Order.objects.filter(
            vendor=vendor,
            status__in=[OrderStatus.CONFIRMED, OrderStatus.PROCESSING],
        ).count()

        revenue_this_month = Order.objects.filter(
            vendor=vendor,
            created_at__gte=month_start,
            status__in=[OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING, OrderStatus.CONFIRMED],
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        total_revenue = Order.objects.filter(
            vendor=vendor,
            status__in=[OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING, OrderStatus.CONFIRMED],
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        # Recent orders
        recent_orders = Order.objects.filter(vendor=vendor).order_by('-created_at')[:5]
        from apps.orders.serializers import OrderSerializer
        recent_orders_data = OrderSerializer(recent_orders, many=True).data

        return Response({
            'schools': {
                'approved': schools_count,
                'pending': pending_schools,
            },
            'products': {
                'active': products_count,
                'total_variants': total_variants,
                'low_stock': low_stock_count,
                'out_of_stock': out_of_stock_count,
            },
            'orders': {
                'pending': pending_orders,
                'processing': processing_orders,
            },
            'revenue': {
                'this_month': float(revenue_this_month),
                'total': float(total_revenue),
            },
            'recent_orders': recent_orders_data,
        })


# ─── Admin-facing vendor management ──────────────────────────────────────────

class AdminVendorCreateView(generics.CreateAPIView):
    """
    POST /api/v1/admin/vendors/create/
    Admin manually registers a vendor and links them to a target school.
    """
    serializer_class = AdminVendorCreateSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = serializer.save()
        return Response(VendorSerializer(vendor).data, status=status.HTTP_201_CREATED)


class AdminVendorListView(generics.ListAPIView):
    """GET /api/v1/admin/vendors/ — Admin lists all vendors."""
    serializer_class = VendorSerializer
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.select_related('user').all()
    search_fields = ['business_name', 'user__email']
    filterset_fields = ['is_approved']


class AdminVendorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/admin/vendors/{id}/ — Admin manages a vendor."""
    serializer_class = VendorSerializer
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.select_related('user').all()


class AdminVendorApproveView(generics.UpdateAPIView):
    """PATCH /api/v1/admin/vendors/{id}/approve/ — Admin approves/revokes vendor."""
    serializer_class = VendorApprovalSerializer
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.all()

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        approve = request.data.get('is_approved', True)
        vendor.is_approved = approve
        vendor.approved_at = timezone.now() if approve else None
        vendor.save()
        return Response(VendorSerializer(vendor).data)


class VendorCustomerListView(APIView):
    """GET /api/v1/vendors/customers/ — Aggregated customers (parents) who have ordered from vendor."""
    permission_classes = [IsVendor]

    def get(self, request):
        vendor = request.user.vendor_profile
        from apps.orders.models import Order
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get all distinct parents who have placed an order with this vendor
        orders = Order.objects.filter(vendor=vendor).select_related('student_profile__parent', 'school')

        # Aggregate per parent
        customer_map = {}
        for order in orders:
            parent = order.student_profile.parent
            if parent.id not in customer_map:
                customer_map[parent.id] = {
                    'id':           parent.id,
                    'name':         parent.full_name,
                    'email':        parent.email,
                    'phone':        parent.phone,
                    'order_count':  0,
                    'total_spend':  0,
                    'schools':      set(),
                    'last_order':   None,
                }
            c = customer_map[parent.id]
            c['order_count'] += 1
            c['total_spend']  = float(c['total_spend']) + float(order.total_amount)
            c['schools'].add(order.school.name if order.school else '')
            if c['last_order'] is None or order.created_at > c['last_order']:
                c['last_order'] = order.created_at

        customers = []
        for c in customer_map.values():
            c['schools'] = list(c['schools'])
            c['total_spend'] = round(c['total_spend'], 2)
            c['last_order'] = c['last_order'].isoformat() if c['last_order'] else None
            customers.append(c)

        customers.sort(key=lambda x: x['total_spend'], reverse=True)
        return Response(customers)


class VendorAnalyticsView(APIView):
    """GET /api/v1/vendors/analytics/ — Revenue and order analytics."""
    permission_classes = [IsVendor]

    def get(self, request):
        vendor = request.user.vendor_profile
        from apps.orders.models import Order, OrderStatus
        from apps.products.models import Product
        from django.db.models import Sum, Count
        import datetime

        now = timezone.now().date()

        # Last 6 months revenue
        monthly = []
        for i in range(5, -1, -1):
            # Calculate month start/end
            month_date = now.replace(day=1) - datetime.timedelta(days=i * 28)
            month_date = month_date.replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1)

            rev = Order.objects.filter(
                vendor=vendor,
                created_at__date__gte=month_date,
                created_at__date__lt=next_month,
                status__in=[OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED],
            ).aggregate(total=Sum('total_amount'))['total'] or 0

            monthly.append({
                'month': month_date.strftime('%b %Y'),
                'revenue': float(rev),
            })

        # Orders by status
        status_breakdown = {}
        for s, _ in OrderStatus.choices:
            count = Order.objects.filter(vendor=vendor, status=s).count()
            if count:
                status_breakdown[s] = count

        # Top products by revenue
        from apps.orders.models import OrderItem
        top_products = (
            OrderItem.objects
            .filter(order__vendor=vendor)
            .values('product_name')
            .annotate(total_revenue=Sum('unit_price'), total_qty=Sum('quantity'))
            .order_by('-total_revenue')[:10]
        )

        # Top schools by revenue
        from apps.schools.models import School
        top_schools = (
            Order.objects
            .filter(vendor=vendor, school__isnull=False)
            .values('school__name')
            .annotate(revenue=Sum('total_amount'), orders=Count('id'))
            .order_by('-revenue')[:5]
        )

        return Response({
            'monthly_revenue':   monthly,
            'status_breakdown':  status_breakdown,
            'top_products':      list(top_products),
            'top_schools':       [{'school': s['school__name'], 'revenue': float(s['revenue']), 'orders': s['orders']} for s in top_schools],
        })


class VendorLedgerView(APIView):
    """GET /api/v1/vendors/ledger/ — Financial ledger and payout aggregates."""
    permission_classes = [IsVendor]

    def get(self, request):
        vendor = request.user.vendor_profile
        from apps.orders.models import Order
        from django.db.models import Sum

        # Aggregate amounts based on payout_status
        aggregates = Order.objects.filter(vendor=vendor).values('payout_status').annotate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            total_platform_fee=Sum('platform_fee'),
            total_vendor_payout=Sum('vendor_payout_amount')
        )

        ledger = {
            'pending': {'orders': 0, 'total': 0.0, 'fee': 0.0, 'payout': 0.0},
            'cleared': {'orders': 0, 'total': 0.0, 'fee': 0.0, 'payout': 0.0},
            'settled': {'orders': 0, 'total': 0.0, 'fee': 0.0, 'payout': 0.0},
            'refunded': {'orders': 0, 'total': 0.0, 'fee': 0.0, 'payout': 0.0},
        }

        for row in aggregates:
            status = row['payout_status']
            if status in ledger:
                ledger[status] = {
                    'orders': row['total_orders'],
                    'total': float(row['total_amount'] or 0),
                    'fee': float(row['total_platform_fee'] or 0),
                    'payout': float(row['total_vendor_payout'] or 0),
                }

        # Include detailed breakdown of the last 100 orders for the ledger list
        recent_ledger = Order.objects.filter(vendor=vendor).order_by('-created_at').values(
            'order_number', 'created_at', 'total_amount', 'platform_fee', 'vendor_payout_amount', 'payout_status'
        )[:100]

        return Response({
            'summary': ledger,
            'transactions': list(recent_ledger)
        })
