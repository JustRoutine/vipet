"""
Reservation serializer for the VIPET reservations app.

Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.6, 12.1, 12.2, 12.3,
              12.4, 12.5, 12.6, 21.1, 21.2
"""

from rest_framework import serializers

from apps.reservations.models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Reservation model.

    - Exposes all model fields.
    - The 'client' field is read-only and automatically set to the
      authenticated user in the viewset's perform_create().
    - validate() ensures:
        - The selected pet belongs to the authenticated user (request.user).
        - The selected service has is_available=True.
    """

    class Meta:
        model = Reservation
        fields = [
            "id",
            "client",
            "pet",
            "service",
            "start_date",
            "end_date",
            "notes",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "client", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Cross-field validation:
        - Ensure the pet belongs to the requesting user.
        - Ensure the service is available.
        """
        request = self.context.get("request")
        pet = attrs.get("pet")
        service = attrs.get("service")

        if request and pet:
            if pet.owner_id != request.user.pk:
                raise serializers.ValidationError(
                    {"pet": "You can only make reservations for your own pets."}
                )

        if service and not service.is_available:
            raise serializers.ValidationError(
                {"service": "This service is currently not available."}
            )

        return attrs
