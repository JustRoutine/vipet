from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "service_name",
        "service_category",
        "pet_name",
        "start_date",
        "end_date",
        "quantity",
        "unit_price",
        "num_days",
        "dynamic_discount_amount",
        "loyalty_discount_percentage",
        "loyalty_discount_amount",
        "promotion_name",
        "promotion_discount_amount",
        "final_price",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "client",
        "status",
        "subtotal",
        "total_discount",
        "total_paid",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("order_number", "client__email", "stripe_payment_intent_id")
    readonly_fields = (
        "order_number",
        "stripe_payment_intent_id",
        "created_at",
    )
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "service_name",
        "pet_name",
        "quantity",
        "unit_price",
        "final_price",
    )
    list_filter = ("service_category",)
    search_fields = ("service_name", "pet_name", "order__order_number")
