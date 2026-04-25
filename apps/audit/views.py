from rest_framework import generics
from .models import AuditLog
from apps.users.permissions import IsAdmin
from rest_framework import serializers


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = ('id', 'user', 'user_email', 'action', 'entity_type', 'entity_id', 'ip_address', 'timestamp')


class AuditLogListView(generics.ListAPIView):
    """GET /api/v1/audit/ — Admin views all audit logs."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    queryset = AuditLog.objects.select_related('user').all()
    filterset_fields = ['action', 'entity_type', 'user']
    search_fields = ['entity_type', 'entity_id', 'user__email']
    ordering_fields = ['timestamp']
