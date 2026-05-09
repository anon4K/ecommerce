from rest_framework import generics, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductListSerializer,
    ProductImageSerializer
)


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class ProductListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related('category').prefetch_related('images')
    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductImageUploadView(generics.CreateAPIView):
    serializer_class = ProductImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        product = Product.objects.get(id=product_id)
        serializer.save(product=product)