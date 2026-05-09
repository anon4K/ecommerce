from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    CreateOrderSerializer
)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)


class CartItemAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))

        if not product_id:
            return Response(
                {'error': 'Product ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        quantity = request.data.get('quantity')

        if quantity is None or int(quantity) < 1:
            return Response(
                {'error': 'Quantity must be at least 1.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = int(quantity)
        item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')


class OrderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        cart = serializer.validated_data['cart']
        cart_items = serializer.validated_data['cart_items']

        total_price = sum(
            item.product.price * item.quantity
            for item in cart_items
        )

        order = Order.objects.create(
            user=request.user,
            shipping_address=serializer.validated_data['shipping_address'],
            total_price=total_price
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_purchase=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')