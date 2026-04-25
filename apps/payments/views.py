import razorpay
import hmac
import hashlib
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from apps.orders.models import Order
from apps.users.permissions import IsStudent
from .models import Payment, PaymentStatus
from .serializers import PaymentCreateSerializer, PaymentVerifySerializer, PaymentSerializer


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class PaymentCreateView(APIView):
    """POST /api/v1/payments/create/ — Create a Razorpay order for checkout."""
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.get(pk=serializer.validated_data['order_id'], student_profile__parent=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(order, 'payment') and order.payment.status == PaymentStatus.SUCCESS:
            return Response({'detail': 'Order already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        client = get_razorpay_client()
        amount_paise = int(order.total_amount * 100)  # Razorpay expects paise
        rz_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': order.order_number,
        })

        payment, _ = Payment.objects.update_or_create(
            order=order,
            defaults={
                'gateway': 'razorpay',
                'gateway_order_id': rz_order['id'],
                'amount': order.total_amount,
                'currency': 'INR',
                'status': PaymentStatus.PENDING,
            }
        )

        return Response({
            'razorpay_order_id': rz_order['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
            'order_number': order.order_number,
        })


class PaymentVerifyView(APIView):
    """POST /api/v1/payments/verify/ — Verify Razorpay signature and mark payment successful."""
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Verify signature
        key_secret = settings.RAZORPAY_KEY_SECRET.encode()
        message = f"{data['razorpay_order_id']}|{data['razorpay_payment_id']}".encode()
        expected_signature = hmac.new(key_secret, message, hashlib.sha256).hexdigest()

        if expected_signature != data['razorpay_signature']:
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(gateway_order_id=data['razorpay_order_id'])
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment record not found.'}, status=status.HTTP_404_NOT_FOUND)

        payment.gateway_payment_id = data['razorpay_payment_id']
        payment.gateway_signature = data['razorpay_signature']
        payment.status = PaymentStatus.SUCCESS
        payment.paid_at = timezone.now()
        payment.save()

        # Confirm the order
        payment.order.status = 'confirmed'
        payment.order.save()

        return Response(PaymentSerializer(payment).data)


class PaymentWebhookView(APIView):
    """POST /api/v1/payments/webhook/ — Razorpay webhook handler."""
    permission_classes = []  # Webhook comes from Razorpay, not a user
    authentication_classes = []

    def post(self, request):
        # Verify webhook signature
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        received_sig = request.headers.get('X-Razorpay-Signature', '')
        payload = request.body

        if webhook_secret:
            expected = hmac.new(
                webhook_secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            if expected != received_sig:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        event = request.data.get('event')
        if event == 'payment.failed':
            payment_entity = request.data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            try:
                payment = Payment.objects.get(gateway_order_id=order_id)
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = payment_entity.get('error_description', '')
                payment.save()
            except Payment.DoesNotExist:
                pass

        return Response({'status': 'ok'})
