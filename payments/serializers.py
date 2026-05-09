from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'status',
            'stripe_payment_intent_id', 'created_at'
        ]
        read_only_fields = fields


class CreatePaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()

    def validate_order_id(self, value):
        from orders.models import Order
        request = self.context.get('request')

        try:
            order = Order.objects.get(id=value, user=request.user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")

        if hasattr(order, 'payment') and order.payment.status == 'completed':
            raise serializers.ValidationError("This order has already been paid.")

        self.context['order'] = order
        return value