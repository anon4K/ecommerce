from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 
            'price', 'stock', 'in_stock', 'category', 'category_name', 
            'images', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 
            'in_stock', 'category_name', 
            'primary_image', 'is_active']

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
            return None
