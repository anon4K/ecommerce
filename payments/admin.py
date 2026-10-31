from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'user__username']
    readonly_fields = ['reference', 'amount', 'created_at', 'updated_at']