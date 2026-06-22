"""
Pet form for the VIPET pets app.

Requirements: 7.1, 7.6, 7.10
"""

from django.forms import ModelForm

from apps.core.validators import validate_image_file
from apps.pets.models import Pet


class PetForm(ModelForm):
    """
    ModelForm for creating and updating Pet records.

    - Excludes 'owner' (set in the view from request.user).
    - Validates uploaded photo via the shared image validator (MIME + size).

    Requirements: 7.1, 7.6, 7.10
    """

    class Meta:
        model = Pet
        fields = [
            "name",
            "species",
            "breed",
            "gender",
            "date_of_birth",
            "weight",
            "medical_notes",
            "vaccination_status",
            "photo",
        ]

    def clean_photo(self):
        """Validate the uploaded photo using the shared image validator (max 5 MB)."""
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "read"):
            # Only validate if a new file was uploaded (not an existing stored path).
            validate_image_file(photo, max_size_mb=5)
        return photo
