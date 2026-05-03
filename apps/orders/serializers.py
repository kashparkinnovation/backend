from rest_framework import serializers
from .models import Order, OrderItem, BulkOrder


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()

    class Meta:
        model  = OrderItem
        fields = ('id', 'inventory', 'product_name', 'size', 'color', 'quantity', 'unit_price', 'line_total')


class OrderSerializer(serializers.ModelSerializer):
    items        = OrderItemSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source='student_profile.student_name', read_only=True)
    school_name  = serializers.CharField(source='school.name', read_only=True)
    vendor_name  = serializers.CharField(source='vendor.business_name', read_only=True)
    bulk_order_number = serializers.CharField(source='bulk_order.bulk_order_number', read_only=True, default=None)
    vendor_details = serializers.SerializerMethodField()

    can_cancel   = serializers.ReadOnlyField()
    can_exchange = serializers.ReadOnlyField()

    class Meta:
        model  = Order
        fields = (
            'id', 'order_number', 'bulk_order', 'bulk_order_number',
            'student_profile', 'student_name',
            'school', 'school_name', 'vendor', 'vendor_name', 'vendor_details',
            'status', 'can_cancel', 'can_exchange',
            'subtotal', 'tax_amount', 'shipping_amount', 'discount_amount', 'total_amount',
            'shipping_name', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_pincode', 'shipping_phone',
            'payment_method', 'payment_status',
            'distributed_at', 'cancelled_at', 'cancelled_reason',
            'notes', 'items', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'order_number', 'vendor', 'created_at', 'updated_at')

    def get_vendor_details(self, obj):
        if not obj.vendor:
            return None
        return {
            'address': obj.vendor.address,
            'city': obj.vendor.city,
            'state': obj.vendor.state,
            'pincode': obj.vendor.pincode,
            'email': obj.vendor.contact_email,
            'phone': obj.vendor.contact_phone,
            'gst_number': obj.vendor.gst_number,
        }


class OrderCreateSerializer(serializers.Serializer):
    """Used to place a new order with line items (student-facing)."""
    student_profile  = serializers.IntegerField()
    shipping_name    = serializers.CharField()
    shipping_phone   = serializers.CharField()
    shipping_address = serializers.CharField(required=False, allow_blank=True, default="School Delivery")
    shipping_city    = serializers.CharField(required=False, allow_blank=True, default="")
    shipping_state   = serializers.CharField(required=False, allow_blank=True, default="")
    shipping_pincode = serializers.CharField(required=False, allow_blank=True, default="")
    notes            = serializers.CharField(required=False, allow_blank=True)
    items            = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Order
        fields = ('status',)



# ─── Bulk Order ───────────────────────────────────────────────────────────────

class BulkOrderItemInputSerializer(serializers.Serializer):
    """One line inside a bulk order: identifies a specific student + product variant."""
    roll_number  = serializers.CharField()
    product_sku  = serializers.CharField()
    size         = serializers.CharField()
    color        = serializers.CharField(required=False, allow_blank=True, default='')
    quantity     = serializers.IntegerField(min_value=1)


class BulkOrderCreateSerializer(serializers.Serializer):
    vendor_id = serializers.IntegerField()
    notes     = serializers.CharField(required=False, allow_blank=True)
    items     = BulkOrderItemInputSerializer(many=True)


class BulkOrderSerializer(serializers.ModelSerializer):
    school_name    = serializers.CharField(source='school.name', read_only=True)
    vendor_name    = serializers.CharField(source='vendor.business_name', read_only=True)
    total_orders   = serializers.ReadOnlyField()
    total_amount   = serializers.ReadOnlyField()
    orders         = OrderSerializer(many=True, read_only=True)

    class Meta:
        model  = BulkOrder
        fields = (
            'id', 'bulk_order_number', 'school', 'school_name',
            'vendor', 'vendor_name', 'notes',
            'total_orders', 'total_amount',
            'orders', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'bulk_order_number', 'school', 'vendor', 'created_at', 'updated_at')


class BulkOrderListSerializer(serializers.ModelSerializer):
    """Lightweight list version — without nested orders."""
    school_name  = serializers.CharField(source='school.name', read_only=True)
    vendor_name  = serializers.CharField(source='vendor.business_name', read_only=True)
    total_orders = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()

    class Meta:
        model  = BulkOrder
        fields = (
            'id', 'bulk_order_number', 'school_name', 'vendor_name',
            'notes', 'total_orders', 'total_amount', 'created_at',
        )

# ─── Cart ────────────────────────────────────────────────────────────────────

from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='inventory.product.id', read_only=True)
    school_id = serializers.IntegerField(source='inventory.product.school_id', read_only=True)
    product_name = serializers.CharField(source='inventory.product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    size = serializers.CharField(source='inventory.size', read_only=True)
    color = serializers.CharField(source='inventory.color', read_only=True)
    unit_price = serializers.DecimalField(source='inventory.effective_price', max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ('id', 'inventory', 'quantity', 'product_id', 'school_id', 'product_name', 'product_image', 'size', 'color', 'unit_price', 'total_price')

    def get_product_image(self, obj):
        image = obj.inventory.product.images.filter(is_primary=True).first()
        if not image:
            image = obj.inventory.product.images.first()
        if image and image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return None

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'total_price', 'created_at', 'updated_at')
