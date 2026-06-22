from django.db import models


class Promotion(models.Model):
    """
    Admin-managed promotional offer with percentage or fixed discount,
    applicable to specific services or entire categories within a date range.
    """

    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True, db_index=True)
    target_services = models.ManyToManyField(
        "services.Service", blank=True, related_name="promotions"
    )
    target_categories = models.JSONField(default=list, blank=True)  # list of category strings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["is_active", "-start_date"], name="promo_active_start_idx"
            ),
        ]
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_discount_type_display()})"


class DynamicPricingRule(models.Model):
    """
    Singleton-like configuration: one active set of tiers for boarding services.
    Volume-based per-day rate discounts where longer stays get lower per-day rates.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, default="Boarding Volume Discount")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dynamic Pricing Rule"
        verbose_name_plural = "Dynamic Pricing Rules"

    def __str__(self) -> str:
        return self.name


class DynamicPricingTier(models.Model):
    """
    A single tier within a DynamicPricingRule defining a day range
    and the discount percentage applied to stays within that range.
    """

    id = models.BigAutoField(primary_key=True)
    rule = models.ForeignKey(
        DynamicPricingRule, on_delete=models.CASCADE, related_name="tiers"
    )
    min_days = models.PositiveIntegerField()
    max_days = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2
    )  # 0-50

    class Meta:
        ordering = ["min_days"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    discount_percentage__gte=0, discount_percentage__lte=50
                ),
                name="dp_tier_discount_range",
            ),
            models.CheckConstraint(
                condition=models.Q(min_days__lte=models.F("max_days")),
                name="dp_tier_min_lte_max",
            ),
        ]
        verbose_name = "Dynamic Pricing Tier"
        verbose_name_plural = "Dynamic Pricing Tiers"

    def __str__(self) -> str:
        return f"{self.min_days}-{self.max_days} days: {self.discount_percentage}%"


class LoyaltyTier(models.Model):
    """
    Loyalty discount tier based on completed reservation count.
    Clients with enough completed bookings in a category earn automatic discounts.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)  # e.g. "Bronze", "Silver", "Gold"
    min_bookings = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2
    )  # 1-50

    class Meta:
        ordering = ["min_bookings"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    discount_percentage__gte=1, discount_percentage__lte=50
                ),
                name="loyalty_discount_range",
            ),
        ]
        verbose_name = "Loyalty Tier"
        verbose_name_plural = "Loyalty Tiers"

    def __str__(self) -> str:
        return f"{self.name} ({self.min_bookings}+ bookings: {self.discount_percentage}%)"
