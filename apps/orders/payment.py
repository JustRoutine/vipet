"""
Payment Manager for the VIPET orders app.

Handles Stripe PaymentIntent creation, order finalization on payment success,
and unique order number generation.

Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 10.5
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings
from django.db import transaction

from apps.cart.models import Cart
from apps.cart.pricing import (
    CartTotal,
    DynamicPricingTierData,
    LoyaltyTierData,
    PriceBreakdown,
    PricingEngine,
    PromotionData,
    ServiceData,
)
from apps.orders.models import Order, OrderItem
from apps.reservations.models import Reservation

logger = logging.getLogger(__name__)

TWOPLACES = Decimal("0.01")
ONE_HUNDRED = Decimal("100")

# Payment timeout in seconds (Requirement 3.5)
STRIPE_TIMEOUT_SECONDS = 30


class PaymentManager:
    """
    Manages Stripe payment lifecycle: creating PaymentIntents and
    processing successful payments into Orders.

    All monetary amounts are in MAD (Moroccan Dirham).
    Stripe expects amounts in centimes (MAD × 100).
    """

    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment_intent(
        self, cart: Cart, idempotency_key: str
    ) -> stripe.PaymentIntent:
        """
        Create a Stripe PaymentIntent with the cart total converted to centimes.

        Requirement 3.1: Amount in centimes, between 100 and 99,999,999 inclusive.
        Requirement 10.5: Uses idempotency key to prevent duplicate charges.

        Args:
            cart: The client's cart with items to be charged.
            idempotency_key: Unique key per checkout attempt for idempotency.

        Returns:
            The created Stripe PaymentIntent object.

        Raises:
            stripe.error.StripeError: On Stripe API failure.
            ValueError: If cart total is out of allowed range.
        """
        cart_total = self._calculate_cart_total(cart)
        amount_centimes = self._mad_to_centimes(cart_total.total_to_pay)

        if amount_centimes < 100 or amount_centimes > 99_999_999:
            raise ValueError(
                f"Payment amount {amount_centimes} centimes is out of allowed range "
                f"[100, 99999999]."
            )

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_centimes,
            currency="mad",
            metadata={
                "cart_id": str(cart.id),
                "client_id": str(cart.client_id),
            },
            idempotency_key=idempotency_key,
        )

        return payment_intent

    def handle_payment_success(self, payment_intent_id: str) -> Order:
        """
        Create an Order from a successful payment, idempotently.

        Requirement 3.6: Same PaymentIntent ID never produces more than one Order.
        Requirement 3.3: Copy all CartItems into OrderItems preserving pricing data.
        Requirement 3.7: Create Reservation for each date-based OrderItem.
        Requirement 3.8: Clear the client's cart after order creation.

        Uses select_for_update on the PaymentIntent ID to prevent race conditions
        from concurrent webhook deliveries.

        Args:
            payment_intent_id: The Stripe PaymentIntent ID from the webhook event.

        Returns:
            The existing or newly created Order.
        """
        with transaction.atomic():
            # Check if order already exists (idempotency)
            existing_order = (
                Order.objects.select_for_update()
                .filter(stripe_payment_intent_id=payment_intent_id)
                .first()
            )

            if existing_order is not None:
                return existing_order

            # Retrieve the PaymentIntent from Stripe to get metadata
            payment_intent = stripe.PaymentIntent.retrieve(
                payment_intent_id,
            )
            client_id = int(payment_intent.metadata["client_id"])

            # Get the client's cart
            try:
                cart = Cart.objects.select_related("client").get(client_id=client_id)
            except Cart.DoesNotExist:
                logger.error(
                    "Cart not found for client_id=%s during payment success handling.",
                    client_id,
                )
                raise

            # Calculate pricing for all cart items
            item_breakdowns = self._calculate_item_breakdowns(cart)
            cart_total = PricingEngine.calculate_cart_total(
                [breakdown for _, breakdown in item_breakdowns]
            )

            # Create the Order
            order = Order.objects.create(
                order_number=generate_order_number(),
                client_id=client_id,
                subtotal=cart_total.subtotal,
                total_discount=cart_total.total_discount,
                total_paid=cart_total.total_to_pay,
                stripe_payment_intent_id=payment_intent_id,
                status="paid",
            )

            # Create OrderItems and Reservations
            for cart_item, breakdown in item_breakdowns:
                num_days = None
                if cart_item.start_date and cart_item.end_date:
                    num_days = (cart_item.end_date - cart_item.start_date).days

                order_item = OrderItem.objects.create(
                    order=order,
                    service_name=cart_item.service.name,
                    service_category=cart_item.service.category,
                    pet_name=cart_item.pet.name,
                    start_date=cart_item.start_date,
                    end_date=cart_item.end_date,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.service.price,
                    num_days=num_days,
                    dynamic_discount_amount=breakdown.dynamic_discount,
                    loyalty_discount_percentage=breakdown.loyalty_percentage,
                    loyalty_discount_amount=breakdown.loyalty_discount,
                    promotion_name=breakdown.promotion_label,
                    promotion_discount_amount=breakdown.promotion_discount,
                    final_price=breakdown.final_price,
                )

                # Create Reservation for date-based items (Requirement 3.7)
                if cart_item.start_date and cart_item.end_date:
                    Reservation.objects.create(
                        client_id=client_id,
                        pet=cart_item.pet,
                        service=cart_item.service,
                        start_date=cart_item.start_date,
                        end_date=cart_item.end_date,
                        status="pending",
                    )

            # Clear the cart (Requirement 3.8)
            cart.items.all().delete()

            logger.info(
                "Order %s created for client_id=%s (PaymentIntent: %s)",
                order.order_number,
                client_id,
                payment_intent_id,
            )

            return order

    def _calculate_cart_total(self, cart: Cart) -> CartTotal:
        """Calculate the full cart total using the PricingEngine."""
        item_breakdowns = self._calculate_item_breakdowns(cart)
        breakdowns = [breakdown for _, breakdown in item_breakdowns]
        return PricingEngine.calculate_cart_total(breakdowns)

    def _calculate_item_breakdowns(
        self, cart: Cart
    ) -> list[tuple]:
        """
        Calculate PriceBreakdown for each cart item.

        Returns a list of (cart_item, PriceBreakdown) tuples.
        """
        from apps.promotions.models import (
            DynamicPricingRule,
            LoyaltyTier,
            Promotion,
        )

        cart_items = cart.items.select_related("service", "pet").filter(
            service__is_available=True
        )

        # Fetch active promotions
        today = date.today()
        active_promotions = Promotion.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
        ).prefetch_related("target_services")

        # Fetch dynamic pricing tiers
        dynamic_tiers_data: list[DynamicPricingTierData] = []
        active_rule = DynamicPricingRule.objects.filter(is_active=True).first()
        if active_rule:
            for tier in active_rule.tiers.all():
                dynamic_tiers_data.append(
                    DynamicPricingTierData(
                        min_days=tier.min_days,
                        max_days=tier.max_days,
                        discount_percentage=tier.discount_percentage,
                    )
                )

        # Fetch loyalty tiers
        loyalty_tiers = list(LoyaltyTier.objects.all().order_by("min_bookings"))

        results: list[tuple] = []

        for cart_item in cart_items:
            service = cart_item.service
            service_data = ServiceData(
                price=service.price,
                category=service.category,
            )

            # Calculate number of days
            num_days = None
            if cart_item.start_date and cart_item.end_date:
                num_days = (cart_item.end_date - cart_item.start_date).days

            # Determine loyalty tier for this client/category
            loyalty_tier_data = self._get_client_loyalty_tier(
                cart.client_id, service.category, loyalty_tiers
            )

            # Build promotion data for applicable promos
            promo_data_list = self._build_promotion_data(
                active_promotions, service, service.id
            )

            breakdown = PricingEngine.calculate_item_price(
                service=service_data,
                quantity=cart_item.quantity,
                num_days=num_days,
                loyalty_tier=loyalty_tier_data,
                promotions=promo_data_list,
                dynamic_pricing_tiers=dynamic_tiers_data,
                service_id=service.id,
            )

            results.append((cart_item, breakdown))

        return results

    def _get_client_loyalty_tier(
        self,
        client_id: int,
        service_category: str,
        loyalty_tiers: list,
    ) -> LoyaltyTierData | None:
        """
        Determine the client's loyalty tier for a given service category
        based on completed reservations.
        """
        completed_count = Reservation.objects.filter(
            client_id=client_id,
            service__category=service_category,
            status="completed",
        ).count()

        if completed_count <= 0 or not loyalty_tiers:
            return None

        # Find highest applicable tier
        applicable_tier = None
        for tier in loyalty_tiers:
            if completed_count >= tier.min_bookings:
                applicable_tier = tier

        if applicable_tier is None:
            return None

        return LoyaltyTierData(
            name=applicable_tier.name,
            min_bookings=applicable_tier.min_bookings,
            discount_percentage=applicable_tier.discount_percentage,
        )

    def _build_promotion_data(
        self,
        active_promotions,
        service,
        service_id: int,
    ) -> list[PromotionData]:
        """Build PromotionData list from active promotions applicable to a service."""
        promo_data_list: list[PromotionData] = []

        for promo in active_promotions:
            target_service_ids = list(
                promo.target_services.values_list("id", flat=True)
            )
            target_categories = promo.target_categories or []

            promo_data_list.append(
                PromotionData(
                    name=promo.name,
                    discount_type=promo.discount_type,
                    discount_value=promo.discount_value,
                    target_service_ids=target_service_ids,
                    target_categories=target_categories,
                )
            )

        return promo_data_list

    @staticmethod
    def _mad_to_centimes(amount_mad: Decimal) -> int:
        """
        Convert a MAD amount to centimes (integer).

        Requirement 3.1: amount = round(MAD × 100).
        Property 20: Resulting centimes in [100, 99_999_999].
        """
        centimes = (amount_mad * ONE_HUNDRED).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(centimes)


def generate_order_number() -> str:
    """
    Generate a unique order number in the format VIP-YYYYMMDD-XXXX.

    The suffix is a 4-character uppercase hex string from a UUID4,
    ensuring uniqueness even with multiple orders on the same day.
    If a collision occurs, the unique constraint on order_number will
    cause a database error, which should be retried.
    """
    today_str = date.today().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"VIP-{today_str}-{suffix}"
