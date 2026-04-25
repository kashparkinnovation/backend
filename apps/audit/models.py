from django.db import models
from apps.users.models import CustomUser


class AuditLog(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=10)        # CREATE, UPDATE, DELETE
    entity_type = models.CharField(max_length=100)  # Model name, e.g. 'Order'
    entity_id = models.CharField(max_length=50)     # PK of the affected record
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} on {self.entity_type}#{self.entity_id} by {self.user}'
