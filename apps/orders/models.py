from django.db import models
from apps.students.models import StudentProfile
from apps.schools.models import School
from apps.vendors.models import Vendor
from apps.products.models import ProductInventory
from apps.users.models import CustomUser


class DistributionStatus(models.TextChoices):
    PENDING          = 'pending',          'Pending'
    READY_FOR_PICKUP = 'ready_for_pickup', 'Ready for Pickup'
    COLLECTED        = 'collected',        'Collected'
    RETURNED         = 'returned',         'Returned'


class OrderStatus(models.TextChoices):
    PENDING    = 'pending',    'Pending'
    CONFIRMED  = 'confirmed',  'Confirmed'
    PROCESSING = 'processing', 'Processing'
    SHIPPED    = 'shipped',    'Shipped'
    DELIVERED  = 'delivered',  'Delivered'
    CANCELLED  = 'cancelled',  'Cancelled'
    REFUNDED   = 'refunded',   'Refunded'


class BulkOrder(models.Model):
    """
    A school-initiated group order that splits into individual Orders per student.
    """
    bulk_order_number = models.CharField(max_length=60, unique=True)
    school            = models.ForeignKey(School, on_delete=models.CASCADE, related_name='bulk_orders')
    vendor            = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, related_name='bulk_orders')
    created_by        = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_bulk_orders')
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bulk_orders'
        ordering = ['-created_at']

    def __str__(self):
        return self.bulk_order_number

    def save(self, *args, **kwargs):
        if not self.bulk_order_number:
            import uuid
            self.bulk_order_number = f'BULK-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_amount(self):
        from django.db.models import Sum
        return self.orders.aggregate(total=Sum('total_amount'))['total'] or 0


class Order(models.Model):
    student_profile = models.ForeignKey(
        StudentProfile, on_delete=models.SET_NULL, null=True, related_name='orders'
    )
    school  = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, related_name='orders')
    vendor  = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, related_name='orders')
    bulk_order = models.ForeignKey(
        BulkOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )

    order_number = models.CharField(max_length=50, unique=True)
    status       = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)

    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── Financial / Ledgers ──
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payout_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending Clearance'),
        ('cleared', 'Cleared for Payout'),
        ('settled', 'Settled / Paid'),
        ('refunded', 'Refunded')
    ])

    # Shipping always goes to school
    shipping_name    = models.CharField(max_length=255, blank=True)
    shipping_address = models.TextField(blank=True)
    shipping_city    = models.CharField(max_length=100, blank=True)
    shipping_state   = models.CharField(max_length=100, blank=True)
    shipping_pincode = models.CharField(max_length=10, blank=True)
    shipping_phone   = models.CharField(max_length=20, blank=True)

    # Distribution tracking
    distribution_status = models.CharField(
        max_length=20, choices=DistributionStatus.choices, default=DistributionStatus.PENDING
    )
    distributed_at  = models.DateTimeField(null=True, blank=True)
    distributed_by  = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='distributed_orders'
    )

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f'ORD-{uuid.uuid4().hex[:10].upper()}'
            
        # Calculate platform fee if not already set (typically on initial save with amounts)
        if self.total_amount > 0 and self.platform_fee == 0:
            from apps.vendors.models import PlatformSettings
            settings = PlatformSettings.get_settings()
            fee = (self.total_amount * settings.platform_commission_percent) / 100
            self.platform_fee = round(fee, 2)
            self.vendor_payout_amount = self.total_amount - self.platform_fee

        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(ProductInventory, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=255)  # snapshot at time of order
    size         = models.CharField(max_length=20)
    color        = models.CharField(max_length=50, blank=True)
    quantity     = models.PositiveIntegerField()
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.product_name} x{self.quantity} — {self.order.order_number}'


class DiscountType(models.TextChoices):
    FLAT    = 'flat',    'Flat (₹ off)'
    PERCENT = 'percent', 'Percentage (% off)'


class Coupon(models.Model):
    """
    Vendor-created discount coupon. Can be restricted to specific schools.
    """
    vendor         = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='coupons')
    code           = models.CharField(max_length=50, unique=True)
    description    = models.CharField(max_length=255, blank=True)
    discount_type  = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text='Cap for percent coupons')
    max_uses       = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    used_count     = models.PositiveIntegerField(default=0, editable=False)
    valid_from     = models.DateField()
    valid_until    = models.DateField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)
    # Optionally restrict the coupon to specific schools
    schools        = models.ManyToManyField(School, blank=True, related_name='coupons')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupons'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} ({self.vendor.business_name})'

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.valid_until is not None and self.valid_until < timezone.now().date()

    @property
    def is_exhausted(self):
        return self.max_uses is not None and self.used_count >= self.max_uses


class ReturnRequestStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending'
    APPROVED  = 'approved',  'Approved'
    REJECTED  = 'rejected',  'Rejected'
    COMPLETED = 'completed', 'Completed'


class ReturnRequestType(models.TextChoices):
    RETURN   = 'return',   'Return (Refund)'
    EXCHANGE = 'exchange', 'Exchange (Size/Color)'


class ReturnRequest(models.Model):
    """
    A student/parent initiates a return or exchange request on a delivered order.
    The vendor reviews and approves/rejects.
    """
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    request_type = models.CharField(max_length=10, choices=ReturnRequestType.choices, default=ReturnRequestType.RETURN)
    reason       = models.TextField()
    status       = models.CharField(max_length=20, choices=ReturnRequestStatus.choices, default=ReturnRequestStatus.PENDING)

    # For exchanges
    exchange_size  = models.CharField(max_length=20, blank=True)
    exchange_color = models.CharField(max_length=50, blank=True)

    # Vendor response
    admin_notes  = models.TextField(blank=True)
    reviewed_by  = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_returns'
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'return_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Return#{self.id} — {self.order.order_number} [{self.status}]'

