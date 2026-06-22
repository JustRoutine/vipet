"""
Pet serializer for the VIPET pets app.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 21.1, 21.7, 21.8
"""

from rest_framework import serializers

from apps.pets.models import Pet


class PetSerializer(serializers.ModelSerializer):
    """
    Serializer for the Pet model.

    - Exposes all model fields.
    - The 'owner' field is read-only and automatically set to the
      authenticated user in the viewset's perform_create().
    """

    class Meta:
        model = Pet
        fields = [
            "id",
            "owner",
            "name",
            "species",
            "breed",
            "gender",
            "date_of_birth",
            "weight",
            "medical_notes",
            "vaccination_status",
            "photo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]
