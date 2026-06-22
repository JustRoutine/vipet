"""
Order and OrderItem models for the VIPET orders app.

Requirements: 3.3, 8.1
"""

from django.conf import settings
from django.db import models


class Order(models.Model):
    """
    A finalized purchase record created from a Cart after successful payment.

    Stores the total amount paid, payment metadata (Stripe PaymentIntent ID),
    and references the client who placed the order.
    """

    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    ]

    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(
        max_length=255, unique=True, db_index=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="paid")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(
                fields=["client", "-created_at"], name="order_client_created_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"Order {self.order_number} ({self.status})"


class OrderItem(models.Model):
    """
    A single line item within an Order, preserving the service, pet, price,
    and discount details at the time of purchase.

    All discount breakdown fields are stored to provide a complete audit trail
    of how the final price was calculated.
    """

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service_name = models.CharField(max_length=100)
    service_category = models.CharField(max_length=30)
    pet_name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    num_days = models.PositiveIntegerField(null=True, blank=True)
    dynamic_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    loyalty_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    loyalty_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    promotion_name = models.CharField(max_length=100, blank=True)
    promotion_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    final_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        indexes = [
            models.Index(fields=["order"], name="orderitem_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.service_name} for {self.pet_name} (x{self.quantity})"
