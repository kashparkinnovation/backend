from django.urls import path
from .views import PaymentCreateView, PaymentVerifyView, PaymentWebhookView

app_name = 'payments'

urlpatterns = [
    path('create/', PaymentCreateView.as_view(), name='payment-create'),
    path('verify/', PaymentVerifyView.as_view(), name='payment-verify'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
]
