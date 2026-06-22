"""
Cart serializers for the VIPET REST API.

Provides serializers for Cart and CartItem with computed pricing breakdown
fields, and an AddCartItemSerializer with deduplication logic.

Requirements: 1.1, 1.2, 1.5, 1.6, 1.9, 1.10
"""

from datetime import date

from rest_framework import serializers

from apps.cart.models import Cart, CartItem
from apps.cart.pricing import (
    CartTotal,
    DynamicPricingTierData,
    LoyaltyTierData,
    PriceBreakdown,
    PricingEngine,
    PromotionData,
    ServiceData,
)
from apps.pets.models import Pet
from apps.promotions.models import DynamicPricingRule, LoyaltyTier, Promotion
from apps.reservations.models import Reservation
from apps.services.models import Service


def _get_active_promotions() -> list[PromotionData]:
    """Fetch all currently active promotions as PromotionData objects."""
    today = date.today()
    promos = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    ).prefetch_related("target_services")

    result = []
    for promo in promos:
        result.append(
            PromotionData(
                name=promo.name,
                discount_type=promo.discount_type,
                discount_value=promo.discount_value,
                target_service_ids=list(
                    promo.target_services.values_list("id", flat=True)
                ),
                target_categories=promo.target_categories or [],
            )
        )
    return result


def _get_dynamic_pricing_tiers() -> list[DynamicPricingTierData]:
    """Fetch active dynamic pricing tiers."""
    rule = DynamicPricingRule.objects.filter(is_active=True).first()
    if not rule:
        return []
    return [
        DynamicPricingTierData(
            min_days=tier.min_days,
            max_days=tier.max_days,
            discount_percentage=tier.discount_percentage,
        )
        for tier in rule.tiers.all()
    ]


def _get_loyalty_tier(client, service_category: str) -> LoyaltyTierData | None:
    """
    Determine the applicable loyalty tier for a client in a given service category.

    Requirements 6.1, 6.2, 6.3: Based on completed reservation count for that category.
    """
    completed_count = Reservation.objects.filter(
        client=client,
        service__category=service_category,
        status="completed",
    ).count()

    if completed_count < 1:
        return None

    loyalty_tiers = LoyaltyTier.objects.all().order_by("-min_bookings")
    for tier in loyalty_tiers:
        if completed_count >= tier.min_bookings:
            return LoyaltyTierData(
                name=tier.name,
                min_bookings=tier.min_bookings,
                discount_percentage=tier.discount_percentage,
            )
    return None


def _calculate_item_breakdown(item: CartItem, client) -> PriceBreakdown:
    """Calculate the full price breakdown for a single cart item."""
    service = item.service
    service_data = ServiceData(
        price=service.price,
        category=service.category,
    )

    # Calculate number of days if date range is present
    num_days = None
    if item.start_date and item.end_date:
        num_days = (item.end_date - item.start_date).days

    # Get pricing context
    loyalty_tier = _get_loyalty_tier(client, service.category)
    promotions = _get_active_promotions()
    dynamic_tiers = _get_dynamic_pricing_tiers()

    return PricingEngine.calculate_item_price(
        service=service_data,
        quantity=item.quantity,
        num_days=num_days,
        loyalty_tier=loyalty_tier,
        promotions=promotions,
        dynamic_pricing_tiers=dynamic_tiers,
        service_id=service.id,
    )


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem with computed pricing breakdown fields (read-only).

    Write fields: service, pet, start_date, end_date, quantity.
    Read-only computed fields: pricing breakdown from PricingEngine.

    Requirements: 1.5, 1.6, 1.9
    """

    # Read-only display fields
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_category = serializers.CharField(source="service.category", read_only=True)
    pet_name = serializers.CharField(source="pet.name", read_only=True)
    is_available = serializers.BooleanField(
        source="service.is_available", read_only=True
    )

    # Computed pricing breakdown fields (read-only)
    base_price = serializers.SerializerMethodField()
    dynamic_discount = serializers.SerializerMethodField()
    price_after_dynamic = serializers.SerializerMethodField()
    loyalty_percentage = serializers.SerializerMethodField()
    loyalty_discount = serializers.SerializerMethodField()
    price_after_loyalty = serializers.SerializerMethodField()
    promotion_label = serializers.SerializerMethodField()
    promotion_discount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "service",
            "service_name",
            "service_category",
            "pet",
            "pet_name",
            "start_date",
            "end_date",
            "quantity",
            "is_available",
            # Pricing breakdown (read-only, computed)
            "base_price",
            "dynamic_discount",
            "price_after_dynamic",
            "loyalty_percentage",
            "loyalty_discount",
            "price_after_loyalty",
            "promotion_label",
            "promotion_discount",
            "final_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_quantity(self, value):
        """Quantity must be between 1 and 50 inclusive. Requirements 1.5, 1.6."""
        if value < 1 or value > 50:
            raise serializers.ValidationError(
                "La quantité doit être comprise entre 1 et 50."
            )
        return value

    def _get_breakdown(self, obj: CartItem) -> PriceBreakdown:
        """Get or compute the pricing breakdown for the item, caching on the instance."""
        # Cache the breakdown on the serializer context or instance to avoid recomputation
        cache_key = f"_breakdown_{obj.pk}"
        context_cache = self.context.get("_breakdown_cache")
        if context_cache and cache_key in context_cache:
            return context_cache[cache_key]

        # Get the client from context or from the cart
        client = self.context.get("client") or obj.cart.client
        breakdown = _calculate_item_breakdown(obj, client)

        # Store in context cache if available
        if context_cache is not None:
            context_cache[cache_key] = breakdown

        return breakdown

    def get_base_price(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).base_price)

    def get_dynamic_discount(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).dynamic_discount)

    def get_price_after_dynamic(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).price_after_dynamic)

    def get_loyalty_percentage(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).loyalty_percentage)

    def get_loyalty_discount(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).loyalty_discount)

    def get_price_after_loyalty(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).price_after_loyalty)

    def get_promotion_label(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return ""
        return self._get_breakdown(obj).promotion_label

    def get_promotion_discount(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).promotion_discount)

    def get_final_price(self, obj: CartItem) -> str:
        if not obj.service.is_available:
            return "0.00"
        return str(self._get_breakdown(obj).final_price)


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart with nested items and computed totals.

    Displays: subtotal, total_discount, total_to_pay (all in MAD, 2 decimal places).
    Excludes unavailable service items from totals.

    Requirements: 1.9, 1.10
    """

    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_to_pay = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "item_count",
            "items",
            "subtotal",
            "total_discount",
            "total_to_pay",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _get_cart_data(self, obj: Cart):
        """Compute items serialization and cart totals together."""
        cache_key = "_cart_data"
        if hasattr(obj, cache_key):
            return getattr(obj, cache_key)

        client = self.context.get("client") or obj.client
        items = obj.items.select_related("service", "pet").order_by("-created_at")

        # Build a context with breakdown cache for efficiency
        context = {**self.context, "_breakdown_cache": {}, "client": client}
        item_serializer = CartItemSerializer(items, many=True, context=context)
        serialized_items = item_serializer.data

        # Calculate cart totals using only available items
        available_items = [item for item in items if item.service.is_available]
        breakdowns = [
            _calculate_item_breakdown(item, client) for item in available_items
        ]
        cart_total = PricingEngine.calculate_cart_total(breakdowns)

        data = {
            "items": serialized_items,
            "subtotal": str(cart_total.subtotal),
            "total_discount": str(cart_total.total_discount),
            "total_to_pay": str(cart_total.total_to_pay),
            "item_count": items.count(),
        }
        setattr(obj, cache_key, data)
        return data

    def get_items(self, obj: Cart):
        return self._get_cart_data(obj)["items"]

    def get_subtotal(self, obj: Cart) -> str:
        return self._get_cart_data(obj)["subtotal"]

    def get_total_discount(self, obj: Cart) -> str:
        return self._get_cart_data(obj)["total_discount"]

    def get_total_to_pay(self, obj: Cart) -> str:
        return self._get_cart_data(obj)["total_to_pay"]

    def get_item_count(self, obj: Cart) -> int:
        return self._get_cart_data(obj)["item_count"]


class AddCartItemSerializer(serializers.Serializer):
    """
    Serializer for adding an item to the cart with deduplication logic.

    If the same (service, pet, start_date, end_date) combination already exists,
    increments the quantity instead of creating a duplicate.

    Requirements: 1.1, 1.2, 1.5, 1.6
    """

    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all())
    start_date = serializers.DateField(required=False, allow_null=True, default=None)
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    quantity = serializers.IntegerField(required=False, default=1)

    def validate_quantity(self, value):
        """Quantity must be between 1 and 50 inclusive. Requirements 1.5, 1.6."""
        if value < 1 or value > 50:
            raise serializers.ValidationError(
                "La quantité doit être comprise entre 1 et 50."
            )
        return value

    def validate(self, attrs):
        """
        Cross-field validation:
        - Pet must belong to the authenticated client.
        - If dates are provided, start_date must be before end_date.
        """
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            pet = attrs.get("pet")
            if pet and pet.owner != request.user:
                raise serializers.ValidationError(
                    {"pet": "Cet animal ne vous appartient pas."}
                )

        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date:
            if end_date <= start_date:
                raise serializers.ValidationError(
                    {"end_date": "La date de fin doit être postérieure à la date de début."}
                )

        return attrs

    def create(self, validated_data):
        """
        Create or increment a CartItem.

        Deduplication: If (cart, service, pet, start_date, end_date) already exists,
        increment quantity. Otherwise, create a new CartItem.

        Requirements: 1.1, 1.2
        """
        cart = self.context["cart"]
        service = validated_data["service"]
        pet = validated_data["pet"]
        start_date = validated_data.get("start_date")
        end_date = validated_data.get("end_date")
        quantity = validated_data.get("quantity", 1)

        # Check for existing item with same combination (deduplication)
        existing_item = CartItem.objects.filter(
            cart=cart,
            service=service,
            pet=pet,
            start_date=start_date,
            end_date=end_date,
        ).first()

        if existing_item:
            # Increment quantity, clamping to max 50
            new_quantity = existing_item.quantity + quantity
            if new_quantity > 50:
                raise serializers.ValidationError(
                    {"quantity": "La quantité totale ne peut pas dépasser 50."}
                )
            existing_item.quantity = new_quantity
            existing_item.save()
            return existing_item

        # Create new CartItem
        return CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            start_date=start_date,
            end_date=end_date,
            quantity=quantity,
        )
