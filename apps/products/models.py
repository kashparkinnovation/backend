from django.db import models
from apps.vendors.models import Vendor
from apps.schools.models import School


class ProductCategory(models.TextChoices):
    SHIRT = 'shirt', 'Shirt'
    TROUSER = 'trouser', 'Trouser'
    SKIRT = 'skirt', 'Skirt'
    BLAZER = 'blazer', 'Blazer'
    TIE = 'tie', 'Tie'
    BELT = 'belt', 'Belt'
    SHOES = 'shoes', 'Shoes'
    SOCKS = 'socks', 'Socks'
    SWEATER = 'sweater', 'Sweater'
    JACKET = 'jacket', 'Jacket'
    TRACKSUIT = 'tracksuit', 'Tracksuit'
    SHORTS = 'shorts', 'Shorts'
    OTHER = 'other', 'Other'


class ProductGender(models.TextChoices):
    BOYS = 'boys', 'Boys'
    GIRLS = 'girls', 'Girls'
    UNISEX = 'unisex', 'Unisex'


class Product(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='products', null=True, blank=True,
        help_text='If null, product is available to all vendor schools'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=ProductCategory.choices, default=ProductCategory.OTHER)
    gender = models.CharField(max_length=10, choices=ProductGender.choices, default=ProductGender.UNISEX)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Commission for school (percentage of sale price)
    school_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='School commission % on this product (overrides platform default)'
    )

    # Rich product details
    material = models.CharField(max_length=255, blank=True)
    care_instructions = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')

    # Legacy single image (kept for backward compat)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'

    def __str__(self):
        return f'{self.name} — {self.vendor.business_name}'

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if img:
            return img
        return self.images.first()


class ProductImage(models.Model):
    """Multiple product images, one can be marked primary."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'Image for {self.product.name} ({"primary" if self.is_primary else "secondary"})'

    def save(self, *args, **kwargs):
        # If this is being set as primary, unset all others
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
        # If no other primary exists, make this one primary
        if not ProductImage.objects.filter(product=self.product, is_primary=True).exists():
            ProductImage.objects.filter(pk=self.pk).update(is_primary=True)


class ProductInventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory')
    size = models.CharField(max_length=20)        # XS, S, M, L, XL, or numeric like 28, 30
    color = models.CharField(max_length=50, blank=True)
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='If set, overrides the product base_price for this variant'
    )
    # Per-variant school commission override (if null, falls back to product level)
    school_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Variant-level school commission % (overrides product level if set)'
    )
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_inventory'
        unique_together = ('product', 'size', 'color')

    @property
    def effective_price(self):
        return self.price_override if self.price_override else self.product.base_price

    def __str__(self):
        return f'{self.product.name} | {self.size} {self.color}'
