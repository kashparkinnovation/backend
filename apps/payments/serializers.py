from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id', 'order', 'gateway', 'gateway_order_id', 'gateway_payment_id',
            'amount', 'currency', 'status', 'paid_at', 'created_at'
        )
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class PaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
