from rest_framework import viewsets, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Post, Category
from .serializers import PostSerializer, CategorySerializer
from apps.users.permissions import IsAdmin

class PublicBlogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public API for reading published blog posts.
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED).order_by('-published_at', '-created_at')

    @action(detail=False, methods=['get'])
    def latest(self, request):
        posts = self.get_queryset()[:3]
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)


class AdminBlogViewSet(viewsets.ModelViewSet):
    """
    Admin API for CRUD operations on blog posts.
    """
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        # Auto-publish logic if status is published
        kwargs = {'author': self.request.user}
        if serializer.validated_data.get('status') == Post.Status.PUBLISHED:
            kwargs['published_at'] = timezone.now()
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        instance = self.get_object()
        new_status = serializer.validated_data.get('status', instance.status)
        
        kwargs = {}
        if instance.status != Post.Status.PUBLISHED and new_status == Post.Status.PUBLISHED:
            kwargs['published_at'] = timezone.now()
        
        serializer.save(**kwargs)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

from .models import StaticPage
from .serializers import StaticPageSerializer

class PublicStaticPageDetailView(generics.RetrieveAPIView):
    """
    Public API for reading static pages.
    """
    serializer_class = StaticPageSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    queryset = StaticPage.objects.filter(is_published=True)

class AdminStaticPageViewSet(viewsets.ModelViewSet):
    """
    Admin API for CRUD operations on static CMS pages.
    """
    queryset = StaticPage.objects.all().order_by('title')
    serializer_class = StaticPageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    lookup_field = 'slug'
