"""
Service serializers for the VIPET REST API.

Requirements: 9.5, 9.6, 9.7, 21.1, 21.2, 21.6
"""

from rest_framework import serializers

from apps.services.models import Service


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Service model.

    Price is represented as a string with exactly 2 decimal places (e.g. "25.00")
    to ensure consistent formatting for API consumers.
    """

    price = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        coerce_to_string=True,
    )

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "category",
            "description",
            "price",
            "is_available",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
