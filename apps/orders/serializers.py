"""
Order serializers for the VIPET REST API.

Provides read-only serializers for Order and OrderItem, exposing
order history details including all price breakdown fields.

Requirements: 8.1, 8.2, 8.3
"""

from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for OrderItem.

    Exposes all breakdown fields preserved at time of purchase:
    service name, pet name, dates, quantity, unit price, num_days,
    dynamic/loyalty/promotional discount amounts, and final price.

    Requirements: 8.3
    """

    class Meta:
        model = OrderItem
        fields = [
            "id",
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
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Order with nested OrderItems.

    Exposes: order_number, status, subtotal, total_discount, total_paid,
    stripe_payment_intent_id, created_at, and nested items list.

    Requirements: 8.1, 8.2, 8.3
    """

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "subtotal",
            "total_discount",
            "total_paid",
            "stripe_payment_intent_id",
            "created_at",
            "items",
        ]
        read_only_fields = fields
