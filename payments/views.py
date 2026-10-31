import logging
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .serializers import CreatePaymentIntentSerializer
from .tasks import send_order_confirmation_email

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


def paystack_headers():
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}


def to_kobo(amount):
    return int((amount * 100).quantize(Decimal("1")))


class InitializePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.context["order"]

        if not request.user.email:
            return Response(
                {"error": "Your account needs an email address to pay."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reference = f"order{order.id}-{uuid.uuid4().hex[:12]}"

        try:
            resp = requests.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                headers=paystack_headers(),
                json={
                    "email": request.user.email,
                    "amount": to_kobo(order.total_price),
                    "currency": "NGN",
                    "reference": reference,
                    "callback_url": f"{settings.FRONTEND_URL}/payment/callback",
                    "metadata": {"order_id": order.id},
                },
                timeout=20,
            )
            body = resp.json()
        except (requests.RequestException, ValueError):
            logger.exception("Paystack initialize request failed")
            return Response(
                {"error": "Could not reach the payment provider. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if resp.status_code != 200 or not body.get("status"):
            logger.error("Paystack initialize rejected: %s", body)
            return Response(
                {"error": "Could not start the payment. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "user": request.user,
                "reference": reference,
                "amount": order.total_price,
                "status": "pending",
            },
        )

        return Response(
            {
                "authorization_url": body["data"]["authorization_url"],
                "reference": reference,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response(
                {"error": "reference is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.filter(
            reference=reference, user=request.user
        ).first()
        if payment is None:
            return Response(
                {"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if payment.status == "completed":
            return Response({"status": "success", "order_id": payment.order_id})

        try:
            resp = requests.get(
                f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                headers=paystack_headers(),
                timeout=20,
            )
            body = resp.json()
        except (requests.RequestException, ValueError):
            logger.exception("Paystack verify request failed")
            return Response(
                {"error": "Could not verify the payment right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if resp.status_code != 200 or not body.get("status"):
            logger.error("Paystack verify rejected: %s", body)
            return Response(
                {"error": "Could not verify the payment right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        data = body["data"]
        paystack_status = data.get("status")

        if paystack_status == "success":
            if data.get("amount") != to_kobo(payment.amount) or data.get("currency") != "NGN":
                logger.error("Paystack amount mismatch for %s: %s", reference, data)
                return Response(
                    {"error": "Payment amount mismatch. Please contact support."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                locked = Payment.objects.select_for_update().get(pk=payment.pk)
                first_time = locked.status != "completed"
                if first_time:
                    locked.status = "completed"
                    locked.save(update_fields=["status", "updated_at"])

            if first_time:
                try:
                    send_order_confirmation_email.delay(payment.order_id)
                except Exception:
                    logger.exception("Order confirmation email failed")

            return Response({"status": "success", "order_id": payment.order_id})

        if paystack_status in ("failed", "reversed"):
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
            return Response({"status": "failed", "order_id": payment.order_id})

        return Response({"status": "pending", "order_id": payment.order_id})