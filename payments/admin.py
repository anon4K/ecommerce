from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['stripe_payment_intent_id', 'user__username']
    readonly_fields = ['stripe_payment_intent_id', 'amount', 'created_at', 'updated_at']