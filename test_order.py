import os
import sys
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
import json

orders = Order.objects.filter(items__isnull=False).distinct()
for order in orders:
    print(f"Order: {order.order_number}, Amount: {order.total_amount}")
    data = OrderSerializer(order).data
    print(f"Items: {json.dumps(data.get('items'))}")
    break
