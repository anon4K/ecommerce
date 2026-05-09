from django.urls import path
from . import views


urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartItemAddView.as_view(), name='cart-add-item'),
    path('cart/item/<int:item_id>/', views.CartItemUpdateView.as_view(), name='cart-item-detail'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
]
