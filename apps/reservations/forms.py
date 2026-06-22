"""
Reservation form for the VIPET reservations app.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.9
"""

from django.forms import ModelForm

from apps.reservations.models import Reservation


class ReservationForm(ModelForm):
    """
    ModelForm for creating a Reservation.

    Fields: pet, service, start_date, end_date, notes.
    The client field is excluded and set in the view from request.user.

    In clean():
      - Verifies the selected pet belongs to the authenticated user (request.user).
      - Verifies the selected service has is_available=True.

    The form expects the view to pass the user via form kwargs so that the
    pet queryset can be filtered to show only the user's pets.

    Requirements: 10.1, 10.2, 10.3, 10.6, 10.9
    """

    class Meta:
        model = Reservation
        fields = ["pet", "service", "start_date", "end_date", "notes"]

    def __init__(self, *args, **kwargs):
        """
        Accept a 'user' keyword argument to filter the pet queryset
        to only pets owned by the authenticated client.
        """
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter pet choices to only show pets owned by the current user
        if self.user is not None:
            from apps.pets.models import Pet

            self.fields["pet"].queryset = Pet.objects.filter(owner=self.user)

    def clean(self):
        """
        Validate pet ownership and service availability.

        - The selected pet must belong to the authenticated user.
        - The selected service must have is_available=True.
        """
        cleaned_data = super().clean()
        pet = cleaned_data.get("pet")
        service = cleaned_data.get("service")

        # Validate pet ownership
        if pet and self.user:
            if pet.owner_id != self.user.pk:
                self.add_error(
                    "pet",
                    "Vous ne pouvez faire des réservations que pour vos propres animaux.",
                )

        # Validate service availability
        if service and not service.is_available:
            self.add_error(
                "service",
                "Ce service n'est actuellement pas disponible.",
            )

        return cleaned_data
