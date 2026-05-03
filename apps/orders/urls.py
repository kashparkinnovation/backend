from django.urls import path
from .views import (
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderCancelView,
    SchoolOrderListView,
    SchoolOrderDetailView,
    SchoolOrderDistributionView,
    BulkOrderListCreateView,
    BulkOrderDetailView,
    BulkOrderCSVImportView,
    CartView,
    OrderInvoiceView,
    OrderDeliverySlipView,
)
from .coupon_views import CouponListCreateView, CouponDetailView, CouponToggleView
from .return_views import ReturnRequestCreateView, StudentReturnRequestListView, ReturnRequestActionView

app_name = 'orders'

urlpatterns = [
    # General (vendor / student / school filtered by role)
    path('', OrderListView.as_view(), name='order-list'),
    path('cart/', CartView.as_view(), name='cart-view'),
    path('cart/items/', CartView.as_view(), name='cart-items-view'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<int:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('<int:pk>/invoice/', OrderInvoiceView.as_view(), name='order-invoice'),
    path('<int:pk>/delivery-slip/', OrderDeliverySlipView.as_view(), name='order-delivery-slip'),
    path('<int:pk>/return/', ReturnRequestCreateView.as_view(), name='return-request-create'),

    # Return requests
    path('returns/', StudentReturnRequestListView.as_view(), name='return-list'),
    path('returns/<int:pk>/', ReturnRequestActionView.as_view(), name='return-action'),

    # School-facing — NOTE: specific paths before parameterised ones to avoid ambiguity
    path('school/', SchoolOrderListView.as_view(), name='school-order-list'),
    path('school/bulk/', BulkOrderListCreateView.as_view(), name='bulk-order-list'),
    path('school/bulk/import/', BulkOrderCSVImportView.as_view(), name='bulk-order-import'),
    path('school/bulk/<int:pk>/', BulkOrderDetailView.as_view(), name='bulk-order-detail'),
    path('school/<int:pk>/', SchoolOrderDetailView.as_view(), name='school-order-detail'),
    path('school/<int:pk>/distribute/', SchoolOrderDistributionView.as_view(), name='school-distribute'),

    # Coupons
    path('coupons/', CouponListCreateView.as_view(), name='coupon-list'),
    path('coupons/<int:pk>/', CouponDetailView.as_view(), name='coupon-detail'),
    path('coupons/<int:pk>/toggle/', CouponToggleView.as_view(), name='coupon-toggle'),
]
