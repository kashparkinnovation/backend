import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.products.views import StorefrontProductListView
from rest_framework.test import APIRequestFactory

def test_view():
    factory = APIRequestFactory()
    # Try with school=11
    request = factory.get('/api/v1/store/', {'school': '11'})
    view = StorefrontProductListView.as_view()
    try:
        response = view(request)
        print(f"Status: {response.status_code}")
        if response.status_code == 500:
            print(response.data)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_view()
