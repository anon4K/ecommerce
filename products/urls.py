from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('', views.ProductListCreateView.as_view(), name='product-list'),
    path('my-products/', views.VendorProductListView.as_view(), name='vendor-products'),
    path('become-vendor/', views.BecomeVendorView.as_view(), name='become-vendor'),
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:product_id>/images/', views.ProductImageUploadView.as_view(), name='product-image-upload'),
]