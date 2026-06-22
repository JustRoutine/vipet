"""
Cart and CartItem models for the VIPET cart app.

Requirements: 1.1, 1.2, 1.3, 1.11
"""

from django.conf import settings
from django.db import models


class Cart(models.Model):
    """
    A server-side shopping cart persisted per authenticated client.

    Each client has exactly one cart (OneToOneField), which survives
    browser sessions until explicitly cleared or converted to an Order.
    """

    id = models.BigAutoField(primary_key=True)
    client = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        limit_choices_to={"role": "client"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self) -> str:
        return f"Cart for {self.client}"


class CartItem(models.Model):
    """
    A single line item within a Cart, linking a Service to a Pet
    with optional date range and quantity.

    Unique constraint prevents duplicate items for the same
    (cart, service, pet, start_date, end_date) combination.
    """

    id = models.BigAutoField(primary_key=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE)
    pet = models.ForeignKey("pets.Pet", on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)  # 1-50
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "service", "pet", "start_date", "end_date"],
                name="unique_cart_item",
            ),
        ]
        indexes = [
            models.Index(
                fields=["cart", "-created_at"], name="cartitem_cart_created_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service} for {self.pet} (x{self.quantity})"
