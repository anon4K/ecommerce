from django.db import models
from products.models import Product
from django.contrib.auth.models import User

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'} in {self.cart.user.username}'s cart"
    
    @property
    def subtotal(self):
        return self.quantity * self.product.price

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    # Progress order used to derive the order-level status from its items.
    # An order is only as "advanced" as its least-progressed active item —
    # e.g. it won't show as shipped until every non-cancelled item has shipped.
    STATUS_PROGRESS = ['pending', 'processing', 'shipped', 'delivered']

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    def recalculate_status(self):
        """Derive this order's overall status from its items' individual statuses.

        Rule: cancelled items are ignored unless EVERY item is cancelled (then
        the whole order is cancelled). Otherwise the order's status is whichever
        active status is least advanced — so an order with one vendor's item
        shipped and another still processing shows as "processing" overall.
        """
        statuses = list(self.items.values_list('status', flat=True))
        if not statuses:
            return

        active = [s for s in statuses if s != 'cancelled']

        if not active:
            new_status = 'cancelled'
        else:
            new_status = min(active, key=lambda s: self.STATUS_PROGRESS.index(s))

        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'} in Order #{self.order.id}"

    @property
    def total_price(self):
        return self.quantity * self.price_at_purchase

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.recalculate_status()
