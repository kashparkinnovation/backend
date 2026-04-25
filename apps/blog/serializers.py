from rest_framework import serializers
from .models import Post, Category, StaticPage
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class PostSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'featured_image', 
            'status', 'author', 'author_name', 'category', 'category_id',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'author_name', 'created_at', 'updated_at', 'author']

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.full_name or obj.author.email
        return "Admin"


class StaticPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticPage
        fields = ['id', 'title', 'slug', 'content', 'is_published', 'custom_head', 'custom_body_end', 'updated_at']
        read_only_fields = ['id', 'updated_at']
