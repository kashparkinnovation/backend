import csv
import io
from decimal import Decimal
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Order, OrderItem, BulkOrder, OrderStatus, DistributionStatus
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
    OrderDistributionSerializer,
    BulkOrderCreateSerializer,
    BulkOrderSerializer,
    BulkOrderListSerializer,
)
from apps.users.permissions import IsVendor, IsSchool, IsStudent
from apps.students.models import StudentProfile
from apps.products.models import ProductInventory, Product


# ─── Student-facing ───────────────────────────────────────────────────────────

class OrderListView(generics.ListAPIView):
    """GET /api/v1/orders/ — Vendor: all their orders; School: school orders; Student: own orders."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields  = ['status', 'distribution_status', 'school']

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related(
            'student_profile', 'school', 'vendor', 'bulk_order'
        ).prefetch_related('items')

        if user.role == 'vendor':
            return qs.filter(vendor__user=user)
        elif user.role == 'school':
            school = getattr(user, 'school_profile', None)
            return qs.filter(school=school) if school else Order.objects.none()
        elif user.role == 'student':
            return qs.filter(student_profile__parent=user)
        return Order.objects.none()


class OrderCreateView(APIView):
    """POST /api/v1/orders/create/ — Student places an order."""
    permission_classes = [IsStudent]

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        student = get_object_or_404(StudentProfile, pk=data['student_profile'], parent=request.user)
        if not student.is_verified:
            return Response({'detail': 'Student profile must be verified before placing an order.'}, status=400)

        # Derive vendor from school
        vendor = student.school.vendor

        order = Order.objects.create(
            student_profile  = student,
            school           = student.school,
            vendor           = vendor,
            shipping_name    = data['shipping_name'],
            shipping_address = data['shipping_address'],
            shipping_city    = data['shipping_city'],
            shipping_state   = data['shipping_state'],
            shipping_pincode = data['shipping_pincode'],
            shipping_phone   = data['shipping_phone'],
            notes            = data.get('notes', ''),
        )

        subtotal = Decimal('0')
        for item in data['items']:
            inv = get_object_or_404(ProductInventory, pk=item['inventory_id'])
            qty = int(item['quantity'])
            price = inv.effective_price
            OrderItem.objects.create(
                order        = order,
                inventory    = inv,
                product_name = inv.product.name,
                size         = inv.size,
                color        = inv.color,
                quantity     = qty,
                unit_price   = price,
            )
            subtotal += price * qty

        order.subtotal     = subtotal
        order.total_amount = subtotal
        order.save(update_fields=['subtotal', 'total_amount'])

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class  = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = Order.objects.select_related('student_profile', 'school', 'vendor').prefetch_related('items')
        if user.role == 'vendor':
            return qs.filter(vendor__user=user)
        elif user.role == 'school':
            school = getattr(user, 'school_profile', None)
            return qs.filter(school=school) if school else Order.objects.none()
        elif user.role == 'student':
            return qs.filter(student_profile__parent=user)
        return Order.objects.none()


class OrderStatusUpdateView(APIView):
    """PATCH /api/v1/orders/{pk}/status/ — Vendor updates order status."""
    permission_classes = [IsVendor]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk, vendor__user=request.user)
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Refresh from DB to get the freshly saved status before checking
        order.refresh_from_db()
        if order.status == OrderStatus.DELIVERED:
            order.distribution_status = DistributionStatus.READY_FOR_PICKUP
            order.save(update_fields=['distribution_status'])

        return Response(OrderSerializer(order).data)


# ─── School-facing Orders ─────────────────────────────────────────────────────

class SchoolOrderListView(generics.ListAPIView):
    """GET /api/v1/orders/school/ — School sees all orders for its students."""
    serializer_class  = OrderSerializer
    permission_classes = [IsSchool]
    filterset_fields   = ['status', 'distribution_status']
    search_fields      = ['order_number', 'student_profile__student_name']

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        if not school:
            return Order.objects.none()
        return (
            Order.objects
            .filter(school=school)
            .select_related('student_profile', 'school', 'vendor', 'bulk_order')
            .prefetch_related('items')
        )


class SchoolOrderDetailView(generics.RetrieveAPIView):
    """GET /api/v1/orders/school/{pk}/ — School views full detail of a single order."""
    serializer_class   = OrderSerializer
    permission_classes = [IsSchool]

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        if not school:
            return Order.objects.none()
        return (
            Order.objects
            .filter(school=school)
            .select_related('student_profile', 'school', 'vendor', 'bulk_order')
            .prefetch_related('items')
        )


class SchoolOrderDistributionView(APIView):
    """PATCH /api/v1/orders/school/{pk}/distribute/ — Mark as collected/ready/returned."""
    permission_classes = [IsSchool]

    def patch(self, request, pk):
        school = getattr(request.user, 'school_profile', None)
        order  = get_object_or_404(Order, pk=pk, school=school)

        serializer = OrderDistributionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['distribution_status']
        order.distribution_status = new_status
        if new_status == DistributionStatus.COLLECTED:
            order.distributed_at = timezone.now()
            order.distributed_by = request.user
        order.save(update_fields=['distribution_status', 'distributed_at', 'distributed_by'])

        return Response(OrderSerializer(order).data)


# ─── Bulk Orders — Shared Helper ─────────────────────────────────────────────

def _build_bulk_order(school, vendor, notes, items, created_by):
    """
    Create a BulkOrder and auto-split it into individual Orders per student.
    Returns (bulk_order_instance, list_of_errors).
    This helper is used by both JSON and CSV import endpoints.
    """
    bulk = BulkOrder.objects.create(
        school     = school,
        vendor     = vendor,
        created_by = created_by,
        notes      = notes,
    )

    errors = []
    for line in items:
        roll = line['roll_number']
        sku  = line['product_sku']
        try:
            student = StudentProfile.objects.get(school=school, roll_number=roll, is_verified=True)
        except StudentProfile.DoesNotExist:
            errors.append({'roll_number': roll, 'error': 'Verified student not found'})
            continue

        try:
            inv = ProductInventory.objects.get(
                product__sku=sku, product__school=school,
                size=line['size'], color=line.get('color', ''),
            )
        except ProductInventory.DoesNotExist:
            errors.append({'roll_number': roll, 'sku': sku, 'error': 'Product/variant not found'})
            continue

        qty   = line['quantity']
        price = inv.effective_price

        order = Order.objects.create(
            bulk_order       = bulk,
            student_profile  = student,
            school           = school,
            vendor           = vendor,
            shipping_name    = school.name,
            shipping_address = school.address,
            shipping_city    = school.city,
            shipping_state   = school.state,
            shipping_pincode = school.pincode,
            shipping_phone   = school.contact_phone or '',
        )
        OrderItem.objects.create(
            order        = order,
            inventory    = inv,
            product_name = inv.product.name,
            size         = inv.size,
            color        = inv.color,
            quantity     = qty,
            unit_price   = price,
        )
        total = price * qty
        order.subtotal = order.total_amount = total
        order.save(update_fields=['subtotal', 'total_amount'])

    return bulk, errors


# ─── Bulk Orders ──────────────────────────────────────────────────────────────

class BulkOrderListCreateView(APIView):
    """
    GET  /api/v1/orders/school/bulk/ — List school bulk orders.
    POST /api/v1/orders/school/bulk/ — Create a bulk order (auto-split into individual orders).
    """
    permission_classes = [IsSchool]

    def get(self, request):
        school = getattr(request.user, 'school_profile', None)
        qs = BulkOrder.objects.filter(school=school).select_related('school', 'vendor')
        serializer = BulkOrderListSerializer(qs, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        school = getattr(request.user, 'school_profile', None)
        if not school:
            return Response({'detail': 'No school profile found.'}, status=403)

        serializer = BulkOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.vendors.models import Vendor
        vendor = get_object_or_404(Vendor, pk=data['vendor_id'])

        bulk, errors = _build_bulk_order(
            school     = school,
            vendor     = vendor,
            notes      = data.get('notes', ''),
            items      = data['items'],
            created_by = request.user,
        )

        return Response({
            'bulk_order': BulkOrderSerializer(bulk).data,
            'errors':     errors,
        }, status=status.HTTP_201_CREATED)


class BulkOrderDetailView(generics.RetrieveAPIView):
    """GET /api/v1/orders/school/bulk/{id}/ — Full detail with individual orders."""
    serializer_class  = BulkOrderSerializer
    permission_classes = [IsSchool]

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        return BulkOrder.objects.filter(school=school).prefetch_related('orders__items', 'orders__student_profile')


class BulkOrderCSVImportView(APIView):
    """
    POST /api/v1/orders/school/bulk/import/
    CSV columns: roll_number, product_sku, size, color (optional), quantity
    Form fields: file (CSV), vendor_id (int), notes (optional)
    """
    permission_classes = [IsSchool]
    parser_classes     = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        school = getattr(request.user, 'school_profile', None)
        if not school:
            return Response({'detail': 'No school profile found.'}, status=403)

        csv_file  = request.FILES.get('file')
        vendor_id = request.data.get('vendor_id')
        notes     = request.data.get('notes', '')

        if not csv_file or not vendor_id:
            return Response({'detail': 'file and vendor_id are required.'}, status=400)

        from apps.vendors.models import Vendor
        vendor = get_object_or_404(Vendor, pk=vendor_id)

        decoded = csv_file.read().decode('utf-8-sig')
        reader  = csv.DictReader(io.StringIO(decoded))

        items  = []
        errors = []
        for i, row in enumerate(reader, start=2):
            roll = (row.get('roll_number') or '').strip()
            sku  = (row.get('product_sku') or '').strip()
            size = (row.get('size') or '').strip()
            try:
                qty = int(row.get('quantity', 1))
            except ValueError:
                errors.append({'row': i, 'error': 'Invalid quantity'})
                continue
            if not (roll and sku and size):
                errors.append({'row': i, 'error': 'roll_number, product_sku, size are required'})
                continue
            items.append({
                'roll_number': roll,
                'product_sku': sku,
                'size':        size,
                'color':       (row.get('color') or '').strip(),
                'quantity':    qty,
            })

        if not items:
            return Response({'detail': 'No valid rows found.', 'errors': errors}, status=400)

        # Use the shared helper — clean, no view-reuse hacks
        bulk, build_errors = _build_bulk_order(
            school     = school,
            vendor     = vendor,
            notes      = notes,
            items      = items,
            created_by = request.user,
        )
        errors.extend(build_errors)

        return Response({
            'bulk_order': BulkOrderSerializer(bulk).data,
            'errors':     errors,
        }, status=status.HTTP_201_CREATED)
