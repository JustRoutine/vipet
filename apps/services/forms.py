"""
Service forms for the VIPET services app.

Requirements: 8.1, 8.2, 8.4, 8.5, 8.8
"""

from django.forms import ModelForm

from apps.core.validators import validate_image_file
from apps.services.models import Service


class ServiceForm(ModelForm):
    """
    ModelForm for creating and updating Service records.

    - Validates uploaded image via the shared image validator (MIME + size).
    - All field constraints (name max 100, description max 1000, price range,
      category choices) are enforced by the model field definitions.

    Requirements: 8.1, 8.2, 8.4, 8.5, 8.8
    """

    class Meta:
        model = Service
        fields = [
            "name",
            "category",
            "description",
            "price",
            "is_available",
            "image",
        ]

    def clean_image(self):
        """Validate the uploaded image using the shared image validator (max 5 MB)."""
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "read"):
            validate_image_file(image, max_size_mb=5)
        return image
