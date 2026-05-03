from django.db import models
from apps.students.models import StudentProfile
from apps.schools.models import School
from apps.vendors.models import Vendor
from apps.products.models import ProductInventory
from apps.users.models import CustomUser


class OrderStatus(models.TextChoices):
    PLACED               = 'placed',               '01 Placed'
    AWAITING_CONFIRMATION = 'awaiting_confirmation', '02 Awaiting Confirmation'
    CONFIRMED            = 'confirmed',            '03 Confirmed'
    PROCESSING           = 'processing',           '04 Processing'
    SHIPPED              = 'shipped',              '05 Shipped'
    DELIVERED            = 'delivered',            '06 Delivered'
    DISTRIBUTED          = 'distributed',          '07 Distributed'
    CANCELLED            = 'cancelled',            '08 Cancelled'
    REFUNDED             = 'refunded',             '09 Refunded'


# Statuses from which a customer/school can cancel
CANCELLABLE_STATUSES = {
    OrderStatus.PLACED,
    OrderStatus.AWAITING_CONFIRMATION,
    OrderStatus.CONFIRMED,
}

# Statuses after which exchange can be raised (only DISTRIBUTED)
EXCHANGEABLE_STATUSES = {OrderStatus.DISTRIBUTED}


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
            self.bulk_order_number = _generate_bulk_order_number()
        super().save(*args, **kwargs)

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_amount(self):
        from django.db.models import Sum
        return self.orders.aggregate(total=Sum('total_amount'))['total'] or 0


def _generate_order_number():
    """
    Generates sequential order numbers in format: YYYY-YY-MM-NNNN
    e.g. 2025-26-05-0001
    Financial year: April → March (2025-26 runs Apr 2025 – Mar 2026)
    Sequence resets each financial year.
    """
    from django.utils import timezone
    from django.db.models import Max
    import re

    now = timezone.now()
    year = now.year
    month = now.month

    # Financial year calculation
    if month >= 4:
        fy_start = year
        fy_end = str(year + 1)[-2:]      # e.g. "26"
    else:
        fy_start = year - 1
        fy_end = str(year)[-2:]          # e.g. "25"

    prefix = f'{fy_start}-{fy_end}-{month:02d}-'

    # Find the highest sequence in this financial year prefix
    result = (
        Order.objects
        .filter(order_number__startswith=f'{fy_start}-{fy_end}-')
        .aggregate(Max('order_number'))['order_number__max']
    )

    seq = 1
    if result:
        # Extract sequence from last segment, e.g. "2025-26-05-0003" → 3
        try:
            seq = int(result.rsplit('-', 1)[-1]) + 1
        except (ValueError, IndexError):
            seq = 1

    return f'{prefix}{seq:04d}'


def _generate_bulk_order_number():
    from django.utils import timezone
    now = timezone.now()
    year, month = now.year, now.month
    fy_start = year if month >= 4 else year - 1
    fy_end = str(fy_start + 1)[-2:]
    prefix = f'BULK-{fy_start}-{fy_end}-{month:02d}-'
    result = (
        BulkOrder.objects
        .filter(bulk_order_number__startswith=f'BULK-{fy_start}-{fy_end}-')
        .aggregate(models.Max('bulk_order_number'))['bulk_order_number__max']
    )
    seq = 1
    if result:
        try:
            seq = int(result.rsplit('-', 1)[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    return f'{prefix}{seq:04d}'


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
    status       = models.CharField(
        max_length=25, choices=OrderStatus.choices, default=OrderStatus.PLACED
    )

    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Financial
    platform_fee         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payout_status        = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending Clearance'),
        ('cleared', 'Cleared for Payout'),
        ('settled', 'Settled / Paid'),
        ('refunded', 'Refunded'),
    ])

    # Shipping always goes to school
    shipping_name    = models.CharField(max_length=255, blank=True)
    shipping_address = models.TextField(blank=True)
    shipping_city    = models.CharField(max_length=100, blank=True)
    shipping_state   = models.CharField(max_length=100, blank=True)
    shipping_pincode = models.CharField(max_length=10, blank=True)
    shipping_phone   = models.CharField(max_length=20, blank=True)

    # Payment
    payment_method  = models.CharField(max_length=30, default='pay_at_school',
                                        choices=[('pay_at_school', 'Pay at School'), ('online', 'Online')])
    payment_status  = models.CharField(max_length=20, default='pending',
                                       choices=[('pending', 'Pending'), ('paid', 'Paid'), ('refunded', 'Refunded')])

    # Timestamps
    cancelled_at     = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    distributed_at   = models.DateTimeField(null=True, blank=True)
    distributed_by   = models.ForeignKey(
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
            self.order_number = _generate_order_number()

        if self.total_amount > 0 and self.platform_fee == 0:
            from apps.vendors.models import PlatformSettings
            settings_obj = PlatformSettings.get_settings()
            fee = (self.total_amount * settings_obj.platform_commission_percent) / 100
            self.platform_fee = round(fee, 2)
            self.vendor_payout_amount = self.total_amount - self.platform_fee

        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        return self.status in CANCELLABLE_STATUSES

    @property
    def can_exchange(self):
        """Exchange allowed within 7 days of distribution."""
        if self.status != OrderStatus.DISTRIBUTED:
            return False
        if not self.distributed_at:
            return False
        from django.utils import timezone
        delta = timezone.now() - self.distributed_at
        return delta.days <= 7


class OrderItem(models.Model):
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    inventory    = models.ForeignKey(ProductInventory, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=255)  # snapshot at order time
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
    vendor         = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='coupons')
    code           = models.CharField(max_length=50, unique=True)
    description    = models.CharField(max_length=255, blank=True)
    discount_type  = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses       = models.PositiveIntegerField(null=True, blank=True)
    used_count     = models.PositiveIntegerField(default=0, editable=False)
    valid_from     = models.DateField()
    valid_until    = models.DateField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)
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


# ─── Exchange / Return ────────────────────────────────────────────────────────

class ExchangeStatus(models.TextChoices):
    PENDING          = 'pending',           'Pending Review'
    VENDOR_APPROVED  = 'vendor_approved',   'Vendor Approved'
    PICKUP_SCHEDULED = 'pickup_scheduled',  'Pickup Scheduled'
    PICKED_UP        = 'picked_up',         'Item Picked Up'
    NEW_ITEM_SHIPPED = 'new_item_shipped',  'New Item Shipped'
    NEW_ITEM_DELIVERED = 'new_item_delivered', 'New Item Delivered to School'
    COMPLETED        = 'completed',         'Completed'
    REJECTED         = 'rejected',          'Rejected'


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
    Unified return / exchange request.
    - Student raises exchange after order is DISTRIBUTED (within 7 days)
    - School can raise on behalf of any student in their school
    - Vendor manages the full exchange lifecycle
    - Admin has full visibility
    """
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    request_type = models.CharField(max_length=10, choices=ReturnRequestType.choices,
                                    default=ReturnRequestType.EXCHANGE)
    reason       = models.TextField()

    # Who raised it
    raised_by    = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name='raised_return_requests'
    )
    raised_by_school = models.BooleanField(default=False,
                                           help_text='True if raised by school on behalf of student')

    # Exchange details
    exchange_inventory = models.ForeignKey(
        ProductInventory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exchange_requests',
        help_text='New variant requested in exchange'
    )
    exchange_size  = models.CharField(max_length=20, blank=True)
    exchange_color = models.CharField(max_length=50, blank=True)

    # Lifecycle status
    status = models.CharField(
        max_length=25, choices=ExchangeStatus.choices, default=ExchangeStatus.PENDING
    )

    # Vendor response
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_returns'
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)

    # Timeline
    pickup_scheduled_at  = models.DateTimeField(null=True, blank=True)
    picked_up_at         = models.DateTimeField(null=True, blank=True)
    new_item_shipped_at  = models.DateTimeField(null=True, blank=True)
    new_item_delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at         = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'return_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Exchange#{self.id} — {self.order.order_number} [{self.status}]'

    @property
    def within_exchange_window(self):
        """True if raised within 7 days of order distribution."""
        if not self.order.distributed_at:
            return False
        from django.utils import timezone
        return (timezone.now() - self.order.distributed_at).days <= 7


class Cart(models.Model):
    """
    Server-side cart mapped to a CustomUser.
    Each user has exactly one active cart.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    """
    Items inside a Cart. Points to ProductInventory.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(ProductInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'inventory')

    def __str__(self):
        return f"{self.quantity} x {self.inventory.product.name} in Cart {self.cart.id}"

    @property
    def total_price(self):
        return self.quantity * float(self.inventory.effective_price)
