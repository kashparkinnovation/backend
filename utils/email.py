from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_order_confirmation_email(order):
    """Send order confirmation to the student's parent."""
    subject = f'[eSchoolKart] Order Confirmed — {order.order_number}'
    body = (
        f'Dear {order.student_profile.parent.full_name},\n\n'
        f'Your order {order.order_number} has been confirmed.\n'
        f'Total: ₹{order.total_amount}\n\n'
        f'You can track your order at {settings.FRONTEND_URL}/store/orders/{order.id}/\n\n'
        f'Thank you.'
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.student_profile.parent.email],
        fail_silently=True,
    )


def send_vendor_new_order_email(order):
    """Notify the vendor of a new order."""
    subject = f'[eSchoolKart] New Order — {order.order_number}'
    body = (
        f'A new order has been placed.\n'
        f'Order Number: {order.order_number}\n'
        f'School: {order.school.name}\n'
        f'Total: ₹{order.total_amount}\n\n'
        f'Login to your vendor dashboard to process it.'
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.vendor.user.email],
        fail_silently=True,
    )
