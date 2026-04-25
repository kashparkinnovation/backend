from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PublicBlogViewSet, AdminBlogViewSet, AdminCategoryViewSet, PublicStaticPageDetailView, AdminStaticPageViewSet

public_router = DefaultRouter()
public_router.register(r'posts', PublicBlogViewSet, basename='public-posts')

admin_router = DefaultRouter()
admin_router.register(r'posts', AdminBlogViewSet, basename='admin-posts')
admin_router.register(r'categories', AdminCategoryViewSet, basename='admin-categories')
admin_router.register(r'pages', AdminStaticPageViewSet, basename='admin-pages')

urlpatterns = [
    path('pages/<slug:slug>/', PublicStaticPageDetailView.as_view(), name='public-page'),
    path('blog/', include(public_router.urls)),
    path('admin/blog/', include(admin_router.urls)),
]
