from django.urls import path
from .views import (
    StorefrontProductListView, StorefrontProductDetailView,
    VendorProductListCreateView, VendorProductDetailView,
    ProductImageListCreateView, ProductImageDetailView, ProductImageSetPrimaryView,
    InventoryUpdateView, InventoryDeleteView, InventoryBulkCreateView, InventoryListView,
)

app_name = 'products'

urlpatterns = [
    # ── Storefront (student facing) ────────────────────────────────────────────
    path('', StorefrontProductListView.as_view(), name='storefront-list'),
    path('<int:pk>/', StorefrontProductDetailView.as_view(), name='storefront-detail'),

    # ── Vendor product management ──────────────────────────────────────────────
    path('vendor/products/', VendorProductListCreateView.as_view(), name='vendor-product-list'),
    path('vendor/products/<int:pk>/', VendorProductDetailView.as_view(), name='vendor-product-detail'),

    # ── Product images ─────────────────────────────────────────────────────────
    path('vendor/products/<int:product_id>/images/', ProductImageListCreateView.as_view(), name='product-images'),
    path('vendor/products/<int:product_id>/images/<int:image_id>/', ProductImageDetailView.as_view(), name='product-image-delete'),
    path('vendor/products/<int:product_id>/images/<int:image_id>/set-primary/', ProductImageSetPrimaryView.as_view(), name='product-image-set-primary'),

    # ── Inventory ──────────────────────────────────────────────────────────────
    path('vendor/inventory/', InventoryListView.as_view(), name='vendor-inventory-list'),
    path('vendor/inventory/<int:pk>/', InventoryUpdateView.as_view(), name='inventory-update'),
    path('vendor/inventory/<int:pk>/delete/', InventoryDeleteView.as_view(), name='inventory-delete'),
    path('vendor/products/<int:product_id>/inventory/', InventoryBulkCreateView.as_view(), name='inventory-bulk-create'),
]
