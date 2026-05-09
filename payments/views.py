import stripe
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from orders.models import Order
from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentIntentSerializer
from payments.tasks import send_order_confirmation_email


stripe.api_key = settings.STRIPE_SECRET_KEY


class CreatePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        order = serializer.context['order']

        intent = stripe.PaymentIntent.create(
            amount=int(order.total_price * 100),
            currency='usd',
            metadata={'order_id': order.id}
        )

        order.stripe_payment_intent = intent['id']
        order.save()

        return Response({
            'client_secret': intent['client_secret'],
            'payment_intent_id': intent['id'],
        }, status=status.HTTP_201_CREATED)


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payment_intent_id = request.data.get('payment_intent_id')

        if not payment_intent_id:
            return Response(
                {'error': 'payment_intent_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent['status'] != 'succeeded':
            return Response(
                {'error': f"Payment not successful. Status: {intent['status']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.get(stripe_payment_intent=payment_intent_id)

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': request.user,
                'stripe_payment_intent_id': payment_intent_id,
                'amount': order.total_price,
                'status': 'completed'
            }
        )

        if not created:
            payment.status = 'completed'
            payment.save()

        order.status = 'confirmed'
        order.save()

        send_order_confirmation_email.delay(order.id)

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)