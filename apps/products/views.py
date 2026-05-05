from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import Product, ProductImage, ProductInventory
from .serializers import (
    ProductSerializer,
    ProductCreateUpdateSerializer,
    ProductImageSerializer,
    ProductInventorySerializer,
    ProductInventoryDetailSerializer,
    ProductInventoryBulkSerializer,
)
from apps.users.permissions import IsVendor
from apps.schools.models import SchoolApprovalStatus
from rest_framework import permissions


# ─── Storefront (student facing) ─────────────────────────────────────────────

class StorefrontProductListView(generics.ListAPIView):
    """GET /api/v1/store/ — Public product listing (no auth required)."""
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['category', 'school', 'vendor', 'gender']
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['base_price', 'name', 'created_at']

    def get_queryset(self):
        qs = (
            Product.objects
            .filter(
                is_active=True,
                vendor__is_approved=True,
                school__approval_status=SchoolApprovalStatus.APPROVED,
            )
            .select_related('vendor', 'school')
            .prefetch_related('inventory', 'images')
        )
        school_id = self.request.query_params.get('school')
        if school_id:
            qs = qs.filter(school_id=school_id)
        return qs


class StorefrontProductDetailView(generics.RetrieveAPIView):
    """GET /api/v1/store/{id}/ — Product detail (no auth required)."""
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    queryset = (
        Product.objects
        .filter(
            is_active=True,
            vendor__is_approved=True,
            school__approval_status=SchoolApprovalStatus.APPROVED,
        )
        .select_related('vendor', 'school')
        .prefetch_related('inventory', 'images')
    )


# ─── Vendor Product Management ────────────────────────────────────────────────

class VendorProductListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/v1/store/vendor/products/ — Vendor manages their product catalog."""
    permission_classes = [IsVendor]
    filterset_fields = ['category', 'school', 'is_active', 'gender']
    search_fields = ['name', 'sku', 'tags']
    ordering_fields = ['created_at', 'base_price', 'name']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .filter(vendor__user=self.request.user)
            .select_related('school')
            .prefetch_related('inventory', 'images')
        )

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor_profile)


class VendorProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/store/vendor/products/{id}/"""
    permission_classes = [IsVendor]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .filter(vendor__user=self.request.user)
            .prefetch_related('inventory', 'images')
        )


# ─── Product Images ───────────────────────────────────────────────────────────

class ProductImageListCreateView(APIView):
    """
    GET  /api/v1/store/vendor/products/{product_id}/images/  — list images
    POST /api/v1/store/vendor/products/{product_id}/images/  — upload image
    """
    permission_classes = [IsVendor]
    parser_classes = [MultiPartParser, FormParser]

    def _get_product(self, request, product_id):
        return get_object_or_404(Product, pk=product_id, vendor__user=request.user)

    def get(self, request, product_id):
        product = self._get_product(request, product_id)
        images = product.images.all()
        serializer = ProductImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, product_id):
        product = self._get_product(request, product_id)
        # Check if this is the first image → auto set as primary
        is_first = not product.images.exists()
        serializer = ProductImageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product, is_primary=is_first)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductImageDetailView(APIView):
    """
    DELETE /api/v1/store/vendor/products/{product_id}/images/{image_id}/
    """
    permission_classes = [IsVendor]

    def _get_image(self, request, product_id, image_id):
        return get_object_or_404(
            ProductImage,
            pk=image_id,
            product_id=product_id,
            product__vendor__user=request.user,
        )

    def delete(self, request, product_id, image_id):
        image = self._get_image(request, product_id, image_id)
        was_primary = image.is_primary
        image.delete()
        # If we deleted the primary, promote first remaining image
        if was_primary:
            first = ProductImage.objects.filter(product_id=product_id).first()
            if first:
                first.is_primary = True
                first.save(update_fields=['is_primary'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageSetPrimaryView(APIView):
    """PATCH /api/v1/store/vendor/products/{product_id}/images/{image_id}/set-primary/"""
    permission_classes = [IsVendor]

    def patch(self, request, product_id, image_id):
        image = get_object_or_404(
            ProductImage,
            pk=image_id,
            product_id=product_id,
            product__vendor__user=request.user,
        )
        # Unset all others
        ProductImage.objects.filter(product_id=product_id).update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=['is_primary'])
        serializer = ProductImageSerializer(image, context={'request': request})
        return Response(serializer.data)


# ─── Inventory Management ─────────────────────────────────────────────────────

class InventoryUpdateView(generics.UpdateAPIView):
    """PATCH /api/v1/store/vendor/inventory/{id}/ — update stock quantity / price."""
    serializer_class = ProductInventorySerializer
    permission_classes = [IsVendor]

    def get_queryset(self):
        return ProductInventory.objects.filter(product__vendor__user=self.request.user)


class InventoryDeleteView(generics.DestroyAPIView):
    """DELETE /api/v1/store/vendor/inventory/{id}/"""
    serializer_class = ProductInventorySerializer
    permission_classes = [IsVendor]

    def get_queryset(self):
        return ProductInventory.objects.filter(product__vendor__user=self.request.user)


class InventoryBulkCreateView(APIView):
    """
    POST /api/v1/store/vendor/products/{product_id}/inventory/
    Body: { "variants": [{ "size": "M", "color": "White", "quantity": 10, "price_override": null }, ...] }
    Creates or updates each variant (upsert by size+color).
    """
    permission_classes = [IsVendor]

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id, vendor__user=request.user)
        serializer = ProductInventoryBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = []
        for variant in serializer.validated_data['variants']:
            size = variant.get('size', '').strip()
            color = variant.get('color', '').strip()
            qty = variant.get('quantity', 0)
            price_override = variant.get('price_override') or None
            school_commission_percent = variant.get('school_commission_percent') or None

            obj, created = ProductInventory.objects.update_or_create(
                product=product,
                size=size,
                color=color,
                defaults={'quantity': qty, 'price_override': price_override, 'school_commission_percent': school_commission_percent},
            )
            results.append(ProductInventorySerializer(obj).data)

        return Response(results, status=status.HTTP_201_CREATED)


class InventoryListView(generics.ListAPIView):
    """GET /api/v1/store/vendor/inventory/ — All inventory across all vendor products."""
    serializer_class = ProductInventoryDetailSerializer
    permission_classes = [IsVendor]
    filterset_fields = ['product', 'size', 'color']
    search_fields = ['product__name', 'size', 'color']

    def get_queryset(self):
        return (
            ProductInventory.objects
            .filter(product__vendor__user=self.request.user)
            .select_related('product', 'product__school')
            .order_by('product__name', 'size', 'color')
        )
