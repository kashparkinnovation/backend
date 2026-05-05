import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

def test_serializer():
    # Find a product with school=None
    p = Product.objects.filter(school__isnull=True).first()
    if not p:
        print("No product with school=None found. Creating one...")
        from apps.vendors.models import Vendor
        v = Vendor.objects.first()
        p = Product.objects.create(
            vendor=v,
            name="Test Product",
            sku="TEST-SKU-123",
            base_price=100,
            school=None
        )
    
    factory = APIRequestFactory()
    request = factory.get('/')
    serializer = ProductSerializer(p, context={'request': Request(request)})
    try:
        print(serializer.data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_serializer()
