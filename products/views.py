from rest_framework import generics, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.text import slugify
import uuid
from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer, ProductSerializer,
    ProductListSerializer, ProductImageSerializer
)


class IsVendorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (
            request.user.is_staff or
            getattr(request.user.profile, 'is_vendor', False)
        )


class IsProductOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or obj.vendor == request.user


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
        return Product.objects.filter(
            is_active=True
        ).select_related('category', 'vendor').prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsVendorOrAdmin()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name', '')
        slug = slugify(name) + '-' + str(uuid.uuid4())[:8]
        serializer.save(vendor=self.request.user, slug=slug)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related('category', 'vendor').prefetch_related('images')
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [IsProductOwnerOrAdmin]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsProductOwnerOrAdmin()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductImageUploadView(generics.CreateAPIView):
    serializer_class = ProductImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        product = Product.objects.get(id=product_id)
        if product.vendor != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't own this product.")
        serializer.save(product=product)


class VendorProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            vendor=self.request.user
        ).select_related('category').prefetch_related('images')


class BecomeVendorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        shop_name = request.data.get('shop_name', '').strip()
        shop_description = request.data.get('shop_description', '').strip()

        if not shop_name:
            return Response({'error': 'Shop name is required.'}, status=400)

        profile.is_vendor = True
        profile.shop_name = shop_name
        profile.shop_description = shop_description
        profile.save()

        return Response({
            'message': f"Welcome! Your shop '{shop_name}' is now live.",
            'shop_name': shop_name,
            'shop_description': shop_description
        })