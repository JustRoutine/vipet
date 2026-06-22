"""
Pet web views for the VIPET pets app.

All views are protected by ClientRequiredMixin (role='client' only) and
filter querysets by owner=request.user for ownership isolation.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.10, 7.11
"""

from datetime import date

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.mixins import ClientRequiredMixin
from apps.pets.forms import PetForm
from apps.pets.models import Pet
from apps.reservations.models import Reservation


class PetListView(ClientRequiredMixin, ListView):
    """
    Display pets owned by the authenticated client.

    Requirements: 7.2
    """

    model = Pet
    template_name = "pets/pet_list.html"
    context_object_name = "pets"

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)


class PetCreateView(ClientRequiredMixin, CreateView):
    """
    Create a new pet for the authenticated client.

    The owner field is automatically set to request.user.

    Requirements: 7.1, 7.6, 7.10
    """

    model = Pet
    form_class = PetForm
    template_name = "pets/pet_form.html"
    success_url = reverse_lazy("pets:pet_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class PetUpdateView(ClientRequiredMixin, UpdateView):
    """
    Update a pet owned by the authenticated client.

    Queryset is filtered by owner to enforce ownership isolation.

    Requirements: 7.3, 7.5, 7.6, 7.10
    """

    model = Pet
    form_class = PetForm
    template_name = "pets/pet_form.html"
    success_url = reverse_lazy("pets:pet_list")

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)


class PetDeleteView(ClientRequiredMixin, DeleteView):
    """
    Delete a pet owned by the authenticated client.

    Deletion is blocked if the pet has future reservations (end_date >= today).

    Requirements: 7.4, 7.5, 7.11
    """

    model = Pet
    template_name = "pets/pet_confirm_delete.html"
    success_url = reverse_lazy("pets:pet_list")

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check for future reservations before allowing deletion
        has_future_reservations = Reservation.objects.filter(
            pet=self.object,
            end_date__gte=date.today(),
        ).exists()

        if has_future_reservations:
            messages.error(
                request,
                "Cet animal ne peut pas être supprimé car il a des réservations futures.",
            )
            return self.render_to_response(self.get_context_data())

        return self.delete(request, *args, **kwargs)
