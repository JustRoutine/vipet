"""
Promotions serializers for the VIPET REST API.

Provides serializers for Promotion CRUD, DynamicPricingRule configuration
(with nested tiers and contiguity validation), and LoyaltyTier configuration
(with ascending thresholds validation).

Requirements: 5.1, 5.2, 5.7, 5.10, 4.5, 4.6, 6.6, 9.3, 9.6
"""

from datetime import date

from rest_framework import serializers

from apps.promotions.models import (
    DynamicPricingRule,
    DynamicPricingTier,
    LoyaltyTier,
    Promotion,
)


class PromotionSerializer(serializers.ModelSerializer):
    """
    Serializer for Promotion CRUD operations.

    Validates:
    - name is non-empty (max 100 chars)
    - start_date < end_date
    - start_date >= today (on creation)
    - discount_value in [1, 50] for percentage type
    - discount_value in [1.00, 10000.00] for fixed type
    - discount_value > 0 (on update — Requirement 9.3)

    Requirements: 5.1, 5.2, 5.10, 9.3, 9.6
    """

    discount_value = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        coerce_to_string=True,
    )

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "is_active",
            "target_services",
            "target_categories",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Name must be non-empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Le nom de la promotion est obligatoire.")
        return value.strip()

    def validate(self, attrs):
        """
        Cross-field validation for dates and discount value constraints.
        """
        errors = {}

        # Determine if this is a creation or update
        is_creation = self.instance is None

        # Get effective field values (fall back to instance for partial updates)
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        discount_type = attrs.get(
            "discount_type", getattr(self.instance, "discount_type", None)
        )
        discount_value = attrs.get(
            "discount_value", getattr(self.instance, "discount_value", None)
        )

        # Validate start_date < end_date (Requirement 5.2)
        if start_date and end_date:
            if start_date >= end_date:
                errors["end_date"] = (
                    "La date de fin doit être postérieure à la date de début."
                )

        # Validate start_date >= today on creation (Requirement 5.2)
        if is_creation and start_date:
            if start_date < date.today():
                errors["start_date"] = (
                    "La date de début ne peut pas être dans le passé."
                )

        # Validate discount_value based on discount_type (Requirements 5.2, 9.3)
        if discount_value is not None and discount_type:
            if discount_value <= 0:
                errors["discount_value"] = (
                    "La valeur de la remise doit être supérieure à zéro."
                )
            elif discount_type == "percentage":
                if discount_value < 1 or discount_value > 50:
                    errors["discount_value"] = (
                        "La remise en pourcentage doit être comprise entre 1 et 50."
                    )
            elif discount_type == "fixed":
                if discount_value < 1 or discount_value > 10000:
                    errors["discount_value"] = (
                        "La remise fixe doit être comprise entre 1.00 et 10000.00 MAD."
                    )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class DynamicPricingTierSerializer(serializers.ModelSerializer):
    """
    Serializer for a single DynamicPricingTier (nested within the rule serializer).
    """

    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=True,
    )

    class Meta:
        model = DynamicPricingTier
        fields = ["id", "min_days", "max_days", "discount_percentage"]
        read_only_fields = ["id"]


class DynamicPricingRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for DynamicPricingRule with nested tiers.

    Validates tier contiguity:
    - Tiers must cover all days from 1 to 365 without gaps or overlaps.
    - Each tier's discount_percentage must be in [0, 50].
    - Each tier's min_days <= max_days.

    Requirements: 4.5, 4.6
    """

    tiers = DynamicPricingTierSerializer(many=True)

    class Meta:
        model = DynamicPricingRule
        fields = ["id", "name", "is_active", "tiers", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_tiers(self, tiers_data):
        """
        Validate that tiers form a contiguous, non-overlapping coverage
        of days 1 to 365 with valid discount percentages.
        """
        if not tiers_data:
            raise serializers.ValidationError(
                "Au moins un palier de tarification est requis."
            )

        # Validate individual tier fields
        for i, tier in enumerate(tiers_data):
            min_days = tier.get("min_days")
            max_days = tier.get("max_days")
            discount = tier.get("discount_percentage")

            if min_days is None or max_days is None:
                raise serializers.ValidationError(
                    f"Le palier {i + 1} doit définir min_days et max_days."
                )

            if min_days > max_days:
                raise serializers.ValidationError(
                    f"Le palier {i + 1}: min_days ({min_days}) ne peut pas dépasser max_days ({max_days})."
                )

            if discount is not None and (discount < 0 or discount > 50):
                raise serializers.ValidationError(
                    f"Le palier {i + 1}: le pourcentage de remise doit être entre 0 et 50."
                )

        # Sort tiers by min_days to validate contiguity
        sorted_tiers = sorted(tiers_data, key=lambda t: t["min_days"])

        # Check that first tier starts at 1
        if sorted_tiers[0]["min_days"] != 1:
            raise serializers.ValidationError(
                "Les paliers doivent commencer à 1 jour."
            )

        # Check that last tier ends at 365
        if sorted_tiers[-1]["max_days"] != 365:
            raise serializers.ValidationError(
                "Les paliers doivent couvrir jusqu'à 365 jours."
            )

        # Check contiguity: each tier's min_days must equal previous tier's max_days + 1
        for i in range(1, len(sorted_tiers)):
            prev_max = sorted_tiers[i - 1]["max_days"]
            curr_min = sorted_tiers[i]["min_days"]
            if curr_min != prev_max + 1:
                if curr_min <= prev_max:
                    raise serializers.ValidationError(
                        f"Les paliers se chevauchent entre les jours {curr_min} et {prev_max}."
                    )
                else:
                    raise serializers.ValidationError(
                        f"Il y a un écart entre les jours {prev_max} et {curr_min}."
                    )

        return tiers_data

    def update(self, instance, validated_data):
        """
        Replace all tiers with the new configuration on PUT.
        """
        tiers_data = validated_data.pop("tiers", None)

        # Update rule fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace tiers if provided
        if tiers_data is not None:
            instance.tiers.all().delete()
            for tier_data in tiers_data:
                DynamicPricingTier.objects.create(rule=instance, **tier_data)

        return instance


class LoyaltyTierSerializer(serializers.ModelSerializer):
    """
    Serializer for LoyaltyTier configuration.

    Validates:
    - discount_percentage in [1, 50]
    - min_bookings is a positive integer
    - Thresholds are in ascending order (validated at the list level)

    Requirements: 6.6
    """

    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=True,
    )

    class Meta:
        model = LoyaltyTier
        fields = ["id", "name", "min_bookings", "discount_percentage"]
        read_only_fields = ["id"]


class LoyaltyTierListSerializer(serializers.Serializer):
    """
    Wrapping serializer to validate a list of loyalty tiers as a whole,
    enforcing ascending thresholds.

    Requirements: 6.6
    """

    tiers = LoyaltyTierSerializer(many=True)

    def validate_tiers(self, tiers_data):
        """
        Validate that loyalty tier thresholds are in ascending order
        and discount percentages are within valid range.
        """
        if not tiers_data:
            raise serializers.ValidationError(
                "Au moins un palier de fidélité est requis."
            )

        for i, tier in enumerate(tiers_data):
            min_bookings = tier.get("min_bookings")
            discount = tier.get("discount_percentage")

            if min_bookings is None or min_bookings < 1:
                raise serializers.ValidationError(
                    f"Le palier {i + 1}: le seuil minimum de réservations doit être un entier positif."
                )

            if discount is not None and (discount < 1 or discount > 50):
                raise serializers.ValidationError(
                    f"Le palier {i + 1}: le pourcentage de remise doit être entre 1 et 50."
                )

        # Sort by min_bookings and check ascending order
        sorted_tiers = sorted(tiers_data, key=lambda t: t["min_bookings"])

        # Check for duplicate thresholds
        thresholds = [t["min_bookings"] for t in sorted_tiers]
        if len(thresholds) != len(set(thresholds)):
            raise serializers.ValidationError(
                "Les seuils de réservations doivent être uniques."
            )

        return tiers_data

    def update(self, instance_list, validated_data):
        """
        Replace all loyalty tiers with the new configuration.
        """
        tiers_data = validated_data.get("tiers", [])

        # Delete existing tiers
        LoyaltyTier.objects.all().delete()

        # Create new tiers
        created = []
        for tier_data in tiers_data:
            created.append(LoyaltyTier.objects.create(**tier_data))

        return created
