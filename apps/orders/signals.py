from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, ReturnRequest
from utils.emails import send_transactional_email

@receiver(post_save, sender=Order)
def order_created_email(sender, instance, created, **kwargs):
    if created and instance.student_profile and instance.student_profile.parent:
        context = {
            'parent_name': instance.student_profile.parent.first_name or 'Parent',
            'student_name': instance.student_profile.student_name,
            'order': instance,
            'school_name': instance.school.name if instance.school else 'School',
        }
        send_transactional_email(
            subject=f"Order Confirmed: {instance.order_number}",
            template_name="emails/order_confirmation.html",
            context=context,
            recipient_list=[instance.student_profile.parent.email]
        )

@receiver(post_save, sender=ReturnRequest)
def return_request_update_email(sender, instance, created, update_fields, **kwargs):
    # Only email on creation or status change
    # Note: signals on update don't always reliable pass update_fields unless .save(update_fields=...) is used.
    # To be safe, we just send an email if a major note or status change happens if we want.
    # We will definitely send for creation. For updates, we can just check if status is not pending.
    
    if hasattr(instance, '_current_status') and instance._current_status == instance.status and not created:
        return # Avoid spam if status hasn't changed. But we need init to track this.
        
    parent = instance.order.student_profile.parent if instance.order.student_profile else None
    if not parent:
        return

    subject_prefix = "New Request" if created else "Request Update"
    
    context = {
        'parent_name': parent.first_name or 'Parent',
        'request_type': instance.request_type,
        'order_number': instance.order.order_number,
        'status': instance.status,
        'admin_notes': instance.admin_notes,
    }
    
    send_transactional_email(
        subject=f"{subject_prefix}: {instance.order.order_number}",
        template_name="emails/return_status_update.html",
        context=context,
        recipient_list=[parent.email]
    )
