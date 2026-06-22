"""
Pricing Engine for the VIPET cart system.

A pure-function service module that receives data (not Django model instances)
and produces computed results using Decimal arithmetic with ROUND_HALF_UP.

Discount application order: dynamic → loyalty → promotional.
Each intermediate result is rounded to 2 decimal places (half-up).
Final price is clamped to >= 0.00.

Requirements: 4.1, 4.2, 4.3, 5.6, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.4
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")
FIFTY_PERCENT = Decimal("0.50")
ONE_HUNDRED = Decimal("100")


@dataclass(frozen=True)
class PriceBreakdown:
    """Computed price breakdown for a single cart item."""

    base_price: Decimal  # service.price * quantity (or per-day * days * qty)
    dynamic_discount: Decimal  # amount saved from dynamic pricing
    price_after_dynamic: Decimal  # base_price - dynamic_discount
    loyalty_percentage: Decimal  # loyalty tier % applied
    loyalty_discount: Decimal  # amount saved from loyalty
    price_after_loyalty: Decimal  # price_after_dynamic - loyalty_discount
    promotion_label: str  # name of applied promotion (or "")
    promotion_discount: Decimal  # amount saved from promotion
    final_price: Decimal  # final clamped price (>= 0)


@dataclass(frozen=True)
class CartTotal:
    """Aggregated cart totals."""

    subtotal: Decimal  # sum of base prices
    total_discount: Decimal  # sum of all discounts
    total_to_pay: Decimal  # sum of final prices


# ---------------------------------------------------------------------------
# Data Transfer Types (plain dicts/dataclasses accepted by the engine)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServiceData:
    """Plain data representing a service (no Django model dependency)."""

    price: Decimal
    category: str


@dataclass(frozen=True)
class DynamicPricingTierData:
    """Plain data representing a dynamic pricing tier."""

    min_days: int
    max_days: int
    discount_percentage: Decimal


@dataclass(frozen=True)
class LoyaltyTierData:
    """Plain data representing a loyalty tier."""

    name: str
    min_bookings: int
    discount_percentage: Decimal


@dataclass(frozen=True)
class PromotionData:
    """Plain data representing a promotion."""

    name: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: Decimal
    target_service_ids: list[int]
    target_categories: list[str]


# ---------------------------------------------------------------------------
# Pricing Engine
# ---------------------------------------------------------------------------


def _round2(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class PricingEngine:
    """
    Deterministic pricing calculator.

    All methods are static/classmethod — no instance state.
    The engine receives plain data and produces computed results.
    """

    @staticmethod
    def calculate_item_price(
        service: ServiceData,
        quantity: int,
        num_days: int | None,
        loyalty_tier: LoyaltyTierData | None,
        promotions: list[PromotionData],
        dynamic_pricing_tiers: list[DynamicPricingTierData],
        service_id: int | None = None,
    ) -> PriceBreakdown:
        """
        Calculate final price for a single cart item with full breakdown.

        Discount order: dynamic → loyalty → promotional.
        Rounds to 2 decimals at each step. Clamps final price to >= 0.00.
        """
        # Step 0: Calculate base price
        base_price = PricingEngine._calculate_base_price(
            service, quantity, num_days
        )

        # Step 1: Apply dynamic pricing (boarding services with days)
        dynamic_discount, price_after_dynamic = PricingEngine._apply_dynamic_pricing(
            base_price, service, num_days, dynamic_pricing_tiers
        )

        # Step 2: Apply loyalty discount
        loyalty_percentage, loyalty_discount, price_after_loyalty = (
            PricingEngine._apply_loyalty_discount(price_after_dynamic, loyalty_tier)
        )

        # Step 3: Select and apply best promotion
        best_promo = PricingEngine._select_best_promotion(
            promotions, base_price, price_after_loyalty, service, service_id
        )
        promotion_label, promotion_discount = PricingEngine._apply_promotion_discount(
            best_promo, base_price, price_after_loyalty
        )

        # Step 4: Calculate final price and clamp to >= 0.00
        price_after_promo = _round2(price_after_loyalty - promotion_discount)
        final_price = max(ZERO, price_after_promo)

        return PriceBreakdown(
            base_price=base_price,
            dynamic_discount=dynamic_discount,
            price_after_dynamic=price_after_dynamic,
            loyalty_percentage=loyalty_percentage,
            loyalty_discount=loyalty_discount,
            price_after_loyalty=price_after_loyalty,
            promotion_label=promotion_label,
            promotion_discount=promotion_discount,
            final_price=final_price,
        )

    @staticmethod
    def calculate_cart_total(items: list[PriceBreakdown]) -> CartTotal:
        """
        Sum all item breakdowns into cart totals.

        Requirement 7.4: sum of individually calculated item final prices
        equals the displayed cart total.
        """
        subtotal = sum(
            (item.base_price for item in items), ZERO
        )
        total_to_pay = sum(
            (item.final_price for item in items), ZERO
        )
        total_discount = subtotal - total_to_pay

        return CartTotal(
            subtotal=_round2(subtotal),
            total_discount=_round2(total_discount),
            total_to_pay=_round2(total_to_pay),
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_base_price(
        service: ServiceData,
        quantity: int,
        num_days: int | None,
    ) -> Decimal:
        """
        Calculate the base price before any discounts.

        For boarding services with days: price_per_day * days * quantity
        For other services: price * quantity
        """
        if num_days is not None and num_days > 0:
            base = _round2(service.price * Decimal(num_days) * Decimal(quantity))
        else:
            base = _round2(service.price * Decimal(quantity))
        return base

    @staticmethod
    def _apply_dynamic_pricing(
        base_price: Decimal,
        service: ServiceData,
        num_days: int | None,
        tiers: list[DynamicPricingTierData],
    ) -> tuple[Decimal, Decimal]:
        """
        Apply dynamic pricing discount for boarding services.

        Formula: base_rate × days × (1 - tier_discount_percentage)
        The dynamic discount is the difference from the full base price.

        Returns: (dynamic_discount, price_after_dynamic)
        """
        if num_days is None or num_days <= 0 or not tiers:
            return ZERO, base_price

        # Only apply to boarding-type categories
        boarding_categories = {"luxury_suite"}
        if service.category not in boarding_categories:
            return ZERO, base_price

        # Find the applicable tier for the number of days
        applicable_tier: DynamicPricingTierData | None = None
        for tier in tiers:
            if tier.min_days <= num_days <= tier.max_days:
                applicable_tier = tier
                break

        if applicable_tier is None or applicable_tier.discount_percentage == ZERO:
            return ZERO, base_price

        # Calculate discount amount
        discount_rate = applicable_tier.discount_percentage / ONE_HUNDRED
        dynamic_discount = _round2(base_price * discount_rate)
        price_after_dynamic = _round2(base_price - dynamic_discount)

        return dynamic_discount, price_after_dynamic

    @staticmethod
    def _get_loyalty_tier(
        completed_bookings: int,
        loyalty_tiers: list[LoyaltyTierData],
    ) -> LoyaltyTierData | None:
        """
        Select the highest loyalty tier whose min_bookings <= completed_bookings.

        Requirements 6.1, 6.2, 6.3: Tier selection based on completed
        reservation count. If count is below all thresholds, returns None.
        """
        if not loyalty_tiers or completed_bookings <= 0:
            return None

        # Sort by min_bookings descending to find highest applicable tier
        sorted_tiers = sorted(
            loyalty_tiers, key=lambda t: t.min_bookings, reverse=True
        )

        for tier in sorted_tiers:
            if completed_bookings >= tier.min_bookings:
                return tier

        return None

    @staticmethod
    def _apply_loyalty_discount(
        price_after_dynamic: Decimal,
        loyalty_tier: LoyaltyTierData | None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Apply loyalty discount on the dynamically-priced amount.

        Requirement 6.4: Applied after dynamic pricing but before promotional.

        Returns: (loyalty_percentage, loyalty_discount_amount, price_after_loyalty)
        """
        if loyalty_tier is None:
            return ZERO, ZERO, price_after_dynamic

        loyalty_percentage = loyalty_tier.discount_percentage
        discount_rate = loyalty_percentage / ONE_HUNDRED
        loyalty_discount = _round2(price_after_dynamic * discount_rate)
        price_after_loyalty = _round2(price_after_dynamic - loyalty_discount)

        return loyalty_percentage, loyalty_discount, price_after_loyalty

    @staticmethod
    def _select_best_promotion(
        promotions: list[PromotionData],
        base_price: Decimal,
        price_after_loyalty: Decimal,
        service: ServiceData,
        service_id: int | None = None,
    ) -> PromotionData | None:
        """
        Select the single promotion yielding the highest discount amount in MAD.

        Requirements 5.6, 5.8, 5.9:
        - Only one promotion is applied (the best one).
        - Percentage promotions are capped at 50% of base price.
        - Fixed promotions don't go below 0.

        A promotion applies to the item if:
        - service_id is in target_service_ids, OR
        - service.category is in target_categories
        """
        if not promotions:
            return None

        best_promo: PromotionData | None = None
        best_discount = ZERO

        for promo in promotions:
            # Check targeting
            if not PricingEngine._promotion_applies_to_item(
                promo, service, service_id
            ):
                continue

            # Calculate effective discount amount
            discount_amount = PricingEngine._calculate_promotion_discount_amount(
                promo, base_price, price_after_loyalty
            )

            if discount_amount > best_discount:
                best_discount = discount_amount
                best_promo = promo

        return best_promo

    @staticmethod
    def _promotion_applies_to_item(
        promo: PromotionData,
        service: ServiceData,
        service_id: int | None,
    ) -> bool:
        """Check if a promotion targets this service or its category."""
        # If promotion has no targeting at all, it applies to everything
        if not promo.target_service_ids and not promo.target_categories:
            return True

        # Check service-level targeting
        if service_id is not None and service_id in promo.target_service_ids:
            return True

        # Check category-level targeting
        if service.category in promo.target_categories:
            return True

        return False

    @staticmethod
    def _apply_promotion_discount(
        promotion: PromotionData | None,
        base_price: Decimal,
        price_after_loyalty: Decimal,
    ) -> tuple[str, Decimal]:
        """
        Calculate the actual discount amount for the selected promotion.

        Requirements 5.8, 5.9:
        - Percentage: discount = min(value% × base_price, 50% × base_price)
        - Fixed: discount = min(fixed_amount, price_after_loyalty)
          (so final doesn't go below 0)

        Returns: (promotion_label, promotion_discount_amount)
        """
        if promotion is None:
            return "", ZERO

        discount_amount = PricingEngine._calculate_promotion_discount_amount(
            promotion, base_price, price_after_loyalty
        )

        return promotion.name, discount_amount

    @staticmethod
    def _calculate_promotion_discount_amount(
        promo: PromotionData,
        base_price: Decimal,
        price_after_loyalty: Decimal,
    ) -> Decimal:
        """
        Calculate the effective discount amount for a promotion.

        - Percentage: min(value% × base_price, 50% × base_price)
        - Fixed: min(fixed_amount, price_after_loyalty)
        """
        if promo.discount_type == "percentage":
            discount_rate = promo.discount_value / ONE_HUNDRED
            raw_discount = _round2(base_price * discount_rate)
            cap = _round2(base_price * FIFTY_PERCENT)
            return min(raw_discount, cap)
        elif promo.discount_type == "fixed":
            # Fixed discount cannot exceed remaining price (no negative)
            return _round2(min(promo.discount_value, price_after_loyalty))
        else:
            return ZERO
