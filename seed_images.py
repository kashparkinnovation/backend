import os
import django
import requests
from django.core.files.base import ContentFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.products.models import Product, ProductImage

IMAGE_URLS = {
    'shirt': [
        'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=800&q=80'
    ],
    'trouser': [
        'https://images.unsplash.com/photo-1594938298596-70f56fb3cecb?auto=format&fit=crop&w=800&q=80'
    ],
    'skirt': [
        'https://images.unsplash.com/photo-1582114757564-9f79b69b2d86?auto=format&fit=crop&w=800&q=80'
    ],
    'blazer': [
        'https://images.unsplash.com/photo-1559551409-dadc959f76b8?auto=format&fit=crop&w=800&q=80'
    ],
    'tie': [
        'https://images.unsplash.com/photo-1587321035210-91cdb314cd7b?auto=format&fit=crop&w=800&q=80'
    ],
    'belt': [
        'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=800&q=80'
    ],
    'shoes': [
        'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80'
    ],
    'socks': [
        'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=800&q=80'
    ],
    'sweater': [
        'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80'
    ],
    'jacket': [
        'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=800&q=80'
    ],
    'tracksuit': [
        'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80'
    ],
    'shorts': [
        'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?auto=format&fit=crop&w=800&q=80'
    ],
    'other': [
        'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1618354691438-25af04c514c8?auto=format&fit=crop&w=800&q=80'
    ]
}

def seed():
    products = Product.objects.all()
    print(f"Checking {products.count()} products for missing images...")
    
    for product in products:
        has_primary = product.images.filter(is_primary=True).exists()
        has_any = product.images.exists()
        
        if not has_any:
            urls = IMAGE_URLS.get(product.category) or IMAGE_URLS['other']
            print(f"Adding images to {product.name} ({product.category})...")
            
            for index, url in enumerate(urls):
                resp = requests.get(url)
                if resp.status_code == 200:
                    img_name = f"{product.sku}_{index}.jpg"
                    cf = ContentFile(resp.content, name=img_name)
                    
                    ProductImage.objects.create(
                        product=product,
                        image=cf,
                        is_primary=(index == 0),
                        caption=f"{product.name} Image {index+1}"
                    )
            print(f"  -> Added {len(urls)} images.")
        else:
            print(f"Skipping {product.name}, already has {product.images.count()} images.")
            
    print("Done seeding images!")

if __name__ == '__main__':
    seed()
