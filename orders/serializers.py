from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.serializers import ProductSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal', 'added_at']
        read_only_fields = ['id', 'added_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_detail', 'quantity', 'price_at_purchase', 'subtotal']
        read_only_fields = ['id', 'price_at_purchase']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_username', 'status', 'shipping_address',
            'total_price', 'stripe_payment_intent', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'total_price', 'stripe_payment_intent', 'created_at', 'updated_at']


class CreateOrderSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()

    def validate(self, attrs):
        request = self.context.get('request')
        cart = Cart.objects.filter(user=request.user).first()

        if not cart or not cart.items.exists():
            raise serializers.ValidationError("Your cart is empty.")

        cart_items = cart.items.select_related('product')
        for item in cart_items:
            if not item.product.is_active:
                raise serializers.ValidationError(
                    f"{item.product.name} is no longer available."
                )
            if item.product.stock < item.quantity:
                raise serializers.ValidationError(
                    f"Only {item.product.stock} units of {item.product.name} available."
                )

        attrs['cart'] = cart
        attrs['cart_items'] = cart_items
        return attrs