from rest_framework import serializers
from .models import Product, ProductImage, ProductInventory


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'caption', 'is_primary', 'order', 'created_at')
        read_only_fields = ('id', 'created_at')


class ProductInventorySerializer(serializers.ModelSerializer):
    effective_price = serializers.ReadOnlyField()

    class Meta:
        model = ProductInventory
        fields = ('id', 'size', 'color', 'price_override', 'quantity', 'effective_price')


class ProductInventoryDetailSerializer(serializers.ModelSerializer):
    """Extended serializer for the vendor inventory overview — includes product info."""
    effective_price = serializers.ReadOnlyField()
    product = serializers.SerializerMethodField()

    class Meta:
        model = ProductInventory
        fields = ('id', 'size', 'color', 'price_override', 'quantity', 'effective_price', 'product')

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'sku': obj.product.sku,
            'school_name': obj.product.school.name if obj.product.school else None,
        }


class ProductSerializer(serializers.ModelSerializer):
    inventory = ProductInventorySerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True, allow_null=True)
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'vendor', 'vendor_name', 'school', 'school_name',
            'name', 'description', 'sku', 'category', 'gender',
            'base_price', 'material', 'care_instructions', 'tags',
            'image', 'images', 'primary_image_url',
            'is_active', 'inventory', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'vendor', 'created_at', 'updated_at')

    def get_primary_image_url(self, obj):
        request = self.context.get('request')
        primary = obj.primary_image
        if primary and primary.image:
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'school', 'name', 'description', 'sku', 'category', 'gender',
            'base_price', 'material', 'care_instructions', 'tags',
            'image', 'is_active',
        )


class ProductInventoryBulkSerializer(serializers.Serializer):
    """Accepts a list of variants to create/update for a product."""
    variants = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate_variants(self, variants):
        required_keys = {'size', 'quantity'}
        for i, v in enumerate(variants):
            missing = required_keys - set(v.keys())
            if missing:
                raise serializers.ValidationError(
                    f'Variant {i + 1} is missing required fields: {", ".join(missing)}'
                )
            if not isinstance(v.get('quantity'), int) or v['quantity'] < 0:
                raise serializers.ValidationError(f'Variant {i + 1}: quantity must be a non-negative integer.')
        return variants
