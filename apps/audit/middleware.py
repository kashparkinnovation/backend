import json
from .models import AuditLog


AUDITED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
AUDIT_SKIP_PATHS = {'/api/v1/auth/login/', '/api/v1/auth/refresh/', '/api/v1/payments/webhook/'}


class AuditLogMiddleware:
    """
    Automatically logs write operations (POST/PUT/PATCH/DELETE) to AuditLog.
    Skips auth endpoints and webhooks to avoid noise.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.method in AUDITED_METHODS
            and request.path not in AUDIT_SKIP_PATHS
            and hasattr(request, 'user')
            and request.user.is_authenticated
            and response.status_code < 400
        ):
            try:
                # Determine entity type from path, e.g. /api/v1/orders/5/ → Order
                path_parts = [p for p in request.path.split('/') if p]
                entity_type = path_parts[-2] if path_parts[-1].isdigit() else path_parts[-1]
                entity_id = path_parts[-1] if path_parts[-1].isdigit() else ''

                action_map = {'POST': 'CREATE', 'PUT': 'UPDATE', 'PATCH': 'UPDATE', 'DELETE': 'DELETE'}

                AuditLog.objects.create(
                    user=request.user,
                    action=action_map.get(request.method, request.method),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
            except Exception:
                pass  # Never let audit logging break the main flow

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
