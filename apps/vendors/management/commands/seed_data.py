"""
Management command to seed the database with realistic dummy data.
Usage: python manage.py seed_data
"""

import random
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from apps.users.models import CustomUser, UserRole
from apps.vendors.models import Vendor
from apps.schools.models import School, SchoolApprovalStatus
from apps.products.models import Product, ProductInventory, ProductCategory, ProductGender
from apps.students.models import StudentProfile, VerificationRequest, VerificationStatus
from apps.orders.models import Order, OrderItem, OrderStatus


VENDOR_DATA = [
    {'business_name': 'Star Uniforms Pvt Ltd', 'city': 'Mumbai', 'state': 'Maharashtra', 'gst': '27AAAAA0000A1Z5'},
    {'business_name': 'National School Wear Co.', 'city': 'Delhi', 'state': 'Delhi', 'gst': '07BBBBB0000B1Z6'},
    {'business_name': 'Dresswell Apparels', 'city': 'Bengaluru', 'state': 'Karnataka', 'gst': '29CCCCC0000C1Z7'},
    {'business_name': 'Vidya Uniforms House', 'city': 'Chennai', 'state': 'Tamil Nadu', 'gst': '33DDDDD0000D1Z8'},
]

SCHOOL_DATA = [
    ('St. Mary\'s High School', 'SMHS001', 'Mumbai', 'Maharashtra'),
    ('Delhi Public School', 'DPS002', 'Delhi', 'Delhi'),
    ('Kendriya Vidyalaya No. 1', 'KV003', 'Bengaluru', 'Karnataka'),
    ('Ryan International School', 'RYAN004', 'Pune', 'Maharashtra'),
    ('DAV Public School', 'DAV005', 'Chennai', 'Tamil Nadu'),
    ('Springdales School', 'SPD006', 'Delhi', 'Delhi'),
    ('The Heritage School', 'THS007', 'Kolkata', 'West Bengal'),
    ('Amity International School', 'AIS008', 'Noida', 'Uttar Pradesh'),
    ('Podar International School', 'PODAR009', 'Mumbai', 'Maharashtra'),
    ('Christ Junior College', 'CJC010', 'Bengaluru', 'Karnataka'),
]

PRODUCT_TEMPLATES = [
    ('School White Formal Shirt', 'shirt', 'unisex', 450, 'White', '65% Polyester, 35% Cotton'),
    ('Navy Blue Trouser', 'trouser', 'boys', 550, 'Navy Blue', '100% Cotton Twill'),
    ('Grey Skirt', 'skirt', 'girls', 420, 'Grey', '50% Polyester, 50% Viscose'),
    ('School Blazer', 'blazer', 'unisex', 1200, 'Dark Blue', 'Poly-Viscose Blend'),
    ('Striped House Tie', 'tie', 'unisex', 180, 'Multi', 'Microfiber Polyester'),
    ('Black Leather Belt', 'belt', 'unisex', 220, 'Black', 'Synthetic Leather'),
    ('Black School Shoes', 'shoes', 'unisex', 890, 'Black', 'PU Leather'),
    ('White Cotton Socks', 'socks', 'unisex', 120, 'White', '80% Cotton, 20% Spandex'),
    ('V-Neck Sweater', 'sweater', 'unisex', 680, 'Grey', '100% Acrylic Wool'),
    ('Sports Tracksuit', 'tracksuit', 'unisex', 950, 'Navy Blue', '100% Polyester'),
]

SIZES_CLOTHING = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SIZES_TROUSER  = ['26', '28', '30', '32', '34', '36', '38']
SIZES_SHOES    = ['3', '4', '5', '6', '7', '8', '9', '10']


class Command(BaseCommand):
    help = 'Seeds the database with dummy vendor, school, product, and order data.'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding database…')

        vendors = self._create_vendors()
        schools = self._create_schools(vendors)
        students = self._create_students(schools)
        products = self._create_products(vendors, schools)
        self._create_orders(students, schools, products)

        self.stdout.write(self.style.SUCCESS('✅ Done! Database seeded successfully.'))

    def _create_vendors(self):
        self.stdout.write('  Creating vendors…')
        vendors = []
        for i, v in enumerate(VENDOR_DATA):
            email = f'vendor{i + 1}@example.com'
            user, _ = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Vendor{i + 1}',
                    'last_name': 'Owner',
                    'role': UserRole.VENDOR,
                    'is_active': True,
                    'password': make_password('password123'),
                }
            )
            vendor, _ = Vendor.objects.get_or_create(
                user=user,
                defaults={
                    'business_name': v['business_name'],
                    'gst_number': v['gst'],
                    'city': v['city'],
                    'state': v['state'],
                    'pincode': f'{random.randint(100000, 999999)}',
                    'address': f'{random.randint(1, 99)}, Industrial Area, {v["city"]}',
                    'is_approved': True,
                    'approved_at': timezone.now(),
                }
            )
            vendors.append(vendor)
            self.stdout.write(f'    ✓ {vendor.business_name} (login: {email} / password123)')
        return vendors

    def _create_schools(self, vendors):
        self.stdout.write('  Creating schools…')
        schools = []
        for i, (name, code, city, state) in enumerate(SCHOOL_DATA):
            vendor = vendors[i % len(vendors)]
            
            # Create a school login user
            email = f'admin@{code.lower()}.edu.in'
            school_user, _ = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': 'Principal',
                    'last_name': code,
                    'role': UserRole.SCHOOL,
                    'is_active': True,
                    'password': make_password('password123'),
                }
            )

            school, _ = School.objects.get_or_create(
                code=code,
                defaults={
                    'vendor': vendor,
                    'school_user': school_user,
                    'name': name,
                    'city': city,
                    'state': state,
                    'pincode': f'{random.randint(100000, 999999)}',
                    'address': f'Survey No. {random.randint(10, 999)}, {city}',
                    'contact_email': f'principal@{code.lower()}.edu.in',
                    'contact_phone': f'+91 {random.randint(7000000000, 9999999999)}',
                    'approval_status': SchoolApprovalStatus.APPROVED,
                    'approved_at': timezone.now(),
                    'is_active': True,
                }
            )
            schools.append(school)
        self.stdout.write(f'    ✓ {len(schools)} schools created')
        return schools

    def _create_students(self, schools):
        self.stdout.write('  Creating students…')
        students = []
        for school in schools:
            for j in range(3):
                email = f'parent_{school.code.lower()}_{j + 1}@example.com'
                user, _ = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': f'Parent{j + 1}',
                        'last_name': school.code,
                        'role': UserRole.STUDENT,
                        'is_active': True,
                        'password': make_password('password123'),
                    }
                )
                roll = f'{j + 1:02d}'
                profile, _ = StudentProfile.objects.get_or_create(
                    school=school,
                    roll_number=roll,
                    defaults={
                        'parent': user,
                        'student_name': f'Student {j + 1} {school.code}',
                        'class_name': f'Class {random.randint(1, 12)}',
                        'section': random.choice(['A', 'B', 'C']),
                        'student_id': f'STU{school.code}{j + 1:03d}',
                        'is_verified': True,
                    }
                )
                students.append(profile)

                # Create some verification requests
                if j == 0:
                    # student 1 is pending
                    profile.is_verified = False
                    profile.save()
                    VerificationRequest.objects.create(
                        student=profile,
                        status=VerificationStatus.PENDING,
                        request_note="Please verify my child's profile."
                    )
                elif j == 1:
                    # student 2 is rejected
                    profile.is_verified = False
                    profile.save()
                    VerificationRequest.objects.create(
                        student=profile,
                        status=VerificationStatus.REJECTED,
                        request_note="Verifying...",
                        review_note="Roll number mismatch. Please update.",
                        reviewed_by=school.school_user,
                        reviewed_at=timezone.now()
                    )
                else:
                    # student 3 is verified, also add a request that was approved
                    VerificationRequest.objects.create(
                        student=profile,
                        status=VerificationStatus.APPROVED,
                        request_note="Verify me please.",
                        review_note="Approved.",
                        reviewed_by=school.school_user,
                        reviewed_at=timezone.now()
                    )

        self.stdout.write(f'    ✓ {len(students)} student profiles created')
        return students


    def _create_products(self, vendors, schools):
        self.stdout.write('  Creating products…')
        all_products = []
        for school in schools:
            vendor = school.vendor
            for k, (name, category, gender, price, color, material) in enumerate(PRODUCT_TEMPLATES):
                sku = f'{school.code}-{category.upper()[:3]}-{k + 1:03d}'
                product, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        'vendor': vendor,
                        'school': school,
                        'name': f'{school.name} — {name}',
                        'description': f'Official {name.lower()} for students of {school.name}. Made from high-quality {material.lower()} for durability and comfort throughout the school day.',
                        'category': category,
                        'gender': gender,
                        'base_price': Decimal(price),
                        'material': material,
                        'care_instructions': 'Machine wash cold (30°C). Do not bleach. Tumble dry low. Iron on low heat.',
                        'tags': f'{category},{gender},uniform,school,{color.lower()}',
                        'is_active': True,
                    }
                )

                if created:
                    # Add size variants
                    sizes = SIZES_TROUSER if category == 'trouser' else (SIZES_SHOES if category == 'shoes' else SIZES_CLOTHING)
                    for size in sizes:
                        qty = random.randint(0, 50)
                        ProductInventory.objects.create(
                            product=product,
                            size=size,
                            color=color,
                            quantity=qty,
                        )

                all_products.append(product)

        self.stdout.write(f'    ✓ {len(all_products)} products created')
        return all_products

    def _create_orders(self, students, schools, products):
        self.stdout.write('  Creating orders…')
        order_count = 0
        statuses = list(OrderStatus.values)

        for school in schools:
            school_students = [s for s in students if s.school_id == school.id]
            school_products = [p for p in products if p.school_id == school.id]
            if not school_students or not school_products:
                continue

            for _ in range(10):
                student = random.choice(school_students)
                status = random.choice(statuses)

                order = Order.objects.create(
                    student_profile=student,
                    school=school,
                    vendor=school.vendor,
                    order_number=f'ORD-{uuid.uuid4().hex[:10].upper()}',
                    status=status,
                    shipping_name=student.student_name,
                    shipping_address=f'{random.randint(1, 999)}, Sample Street',
                    shipping_city=school.city,
                    shipping_state=school.state,
                    shipping_pincode=school.pincode,
                    shipping_phone=f'+91 {random.randint(7000000000, 9999999999)}',
                )

                subtotal = Decimal('0')
                num_items = random.randint(1, 4)
                sample_products = random.sample(school_products, min(num_items, len(school_products)))

                for prod in sample_products:
                    inv = prod.inventory.order_by('?').first()
                    if not inv:
                        continue
                    qty = random.randint(1, 3)
                    price = inv.effective_price
                    OrderItem.objects.create(
                        order=order,
                        inventory=inv,
                        product_name=prod.name,
                        size=inv.size,
                        color=inv.color,
                        quantity=qty,
                        unit_price=price,
                    )
                    subtotal += price * qty

                order.subtotal = subtotal
                order.total_amount = subtotal
                order.save(update_fields=['subtotal', 'total_amount'])
                order_count += 1

        self.stdout.write(f'    ✓ {order_count} orders created')
