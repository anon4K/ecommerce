from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_order_confirmation_email(order_id):
    from orders.models import Order

    try:
        order = Order.objects.prefetch_related('items__product').get(id=order_id)
    except Order.DoesNotExist:
        return f"Order {order_id} not found."

    user = order.user
    if not user or not user.email:
        return "No user email found."

    items_list = "\n".join([
        f"- {item.quantity} x {item.product.name if item.product else 'Deleted Product'} @ ${item.price_at_purchase}"
        for item in order.items.all()
    ])

    message = f"""
Hi {user.username},

Thank you for your order!

Order #{order.id}
Status: {order.status}

Items:
{items_list}

Total: ${order.total_price}
Shipping to: {order.shipping_address}

We'll notify you when your order ships.

Thanks,
The Shop Team
    """

    send_mail(
        subject=f"Order Confirmation — Order #{order.id}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return f"Confirmation email sent for Order #{order.id}"