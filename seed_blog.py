import os
import sys
import django
from django.utils import timezone
import requests
from django.core.files.base import ContentFile

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.blog.models import Category, Post
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

if not admin_user:
    print("No admin user found. Creating dummy user...")
    admin_user = User.objects.create_superuser('admin@eschoolkart.com', 'adminpass')
    admin_user.first_name = "Admin"
    admin_user.save()

# Categories
cat_guides, _ = Category.objects.get_or_create(name="Guides")
cat_news, _ = Category.objects.get_or_create(name="News")
cat_care, _ = Category.objects.get_or_create(name="Care")

posts_data = [
    {
        "title": "Choosing the Right Uniform Size Online",
        "category": cat_guides,
        "content": "<p>When buying uniforms online, it can be tricky to guarantee the right fit. The good news is, by using our standardized measurement guides available on every product page, you can ensure a flawless fit every time.</p><h3>Measure Twice, Order Once</h3><p>Always use a soft tape measure and stand straight. Key dimensions usually include chest circumference, waist, and inseam. If your child is between sizes, we recommend sizing up to allow room for growth through the academic year.</p>",
        "image_url": "https://images.unsplash.com/photo-1595152772835-219674b2a8a6?auto=format&fit=crop&w=800&q=80"
    },
    {
        "title": "Welcome to the new eSchoolKart Platform",
        "category": cat_news,
        "content": "<p>We are thrilled to unveil the new eSchoolKart platform. Gone are the days of paper catalogs and manual cash payments. Now, parents can simply log in, verify their child's student ID, and unlock their school's official custom storefront.</p><p>We partnered with the top logistics providers to ensure shipping directly to your door or straight to the school campus. Keep an eye on this space for further feature announcements!</p>",
        "image_url": "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=800&q=80"
    },
    {
        "title": "How to Wash and Care for School Blazers",
        "category": cat_care,
        "content": "<p>Blazers are the centerpiece of any formal school uniform, but they are also the most delicate. It's essential to follow strict care instructions to ensure they last the entire term and keep your child looking sharp.</p><h3>Dry Clean Only?</h3><p>Most tailored blazers strongly advise dry-cleaning only to prevent the inner structural fusing from separating from the wool blend. Always spot clean minor spills immediately with cold water and mild soap.</p>",
        "image_url": "https://images.unsplash.com/photo-1582738411706-bfc8e691d1c2?auto=format&fit=crop&w=800&q=80"
    }
]

Post.objects.all().delete()
print("Cleared existing posts.")

for data in posts_data:
    post = Post(
        title=data["title"],
        category=data["category"],
        content=data["content"],
        author=admin_user,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now()
    )
    # Download image
    headers = {'User-Agent': 'Mozilla/5.0'}
    img_resp = requests.get(data["image_url"], headers=headers)
    if img_resp.status_code == 200:
        file_name = f"{post.title.replace(' ', '_').lower()}.jpg"
        post.featured_image.save(file_name, ContentFile(img_resp.content), save=True)
    else:
        print(f"Failed to download image for {post.title}: status {img_resp.status_code}")
    
    post.save()
    print(f"Created post: {post.title}")

print("Seeding complete.")
