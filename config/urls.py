"""
Root URL configuration — all routes namespaced under /api/v1/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Django Admin
    path('django-admin/', admin.site.urls),

    # API Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API v1
    path('api/v1/auth/', include('apps.users.urls', namespace='users')),
    path('api/v1/admin/', include('apps.vendors.admin_urls', namespace='admin-vendors')),
    path('api/v1/vendors/', include('apps.vendors.urls', namespace='vendors')),
    path('api/v1/schools/', include('apps.schools.urls', namespace='schools')),
    path('api/v1/students/', include('apps.students.urls', namespace='students')),
    path('api/v1/store/', include('apps.products.urls', namespace='products')),
    path('api/v1/orders/', include('apps.orders.urls', namespace='orders')),
    path('api/v1/payments/', include('apps.payments.urls', namespace='payments')),
    path('api/v1/audit/', include('apps.audit.urls', namespace='audit')),
    path('api/v1/', include('apps.blog.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
