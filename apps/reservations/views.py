"""
Reservation web views for the VIPET reservations app.

Client views are protected by ClientRequiredMixin (role='client' only).
Admin views are protected by AdminRequiredMixin (role='admin' only).

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.9, 11.1, 11.2, 11.3,
              11.4, 11.6, 11.7, 11.8, 12.1, 12.2
"""

from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from apps.core.mixins import AdminRequiredMixin, ClientRequiredMixin
from apps.reservations.forms import ReservationForm
from apps.reservations.models import Reservation


class ReservationListView(ClientRequiredMixin, ListView):
    """
    Display reservations belonging to the authenticated client.

    Filtered by client=request.user so clients only see their own reservations.
    Ordered by creation date descending (most recent first) via model Meta.

    Requirements: 12.1
    """

    model = Reservation
    template_name = "reservations/reservation_list.html"
    context_object_name = "reservations"

    def get_queryset(self):
        return Reservation.objects.filter(client=self.request.user)


class ReservationCreateView(ClientRequiredMixin, CreateView):
    """
    Create a new reservation for the authenticated client.

    The client field is automatically set to request.user.
    The form's pet queryset is filtered to show only the user's own pets.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.9
    """

    model = Reservation
    form_class = ReservationForm
    template_name = "reservations/reservation_form.html"
    success_url = reverse_lazy("reservations:reservation_list")

    def get_form_kwargs(self):
        """Pass the current user to the form for pet queryset filtering."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the client from request.user before saving."""
        form.instance.client = self.request.user
        return super().form_valid(form)


class ReservationCancelView(ClientRequiredMixin, View):
    """
    Cancel a reservation owned by the authenticated client.

    POST only. Checks:
      - The reservation belongs to the authenticated client (ownership).
      - The reservation is in a cancellable status (pending or approved).

    Uses the model's transition_to() method for state enforcement.

    Requirements: 11.6, 11.7, 11.8
    """

    def post(self, request, pk):
        """Handle the cancel action via POST."""
        reservation = get_object_or_404(Reservation, pk=pk)

        # Check ownership
        if reservation.client_id != request.user.pk:
            messages.error(
                request,
                "Vous n'avez pas la permission d'annuler cette réservation.",
            )
            return redirect("reservations:reservation_list")

        # Attempt the transition
        try:
            reservation.transition_to("cancelled")
            messages.success(request, "Réservation annulée avec succès.")
        except ValueError:
            messages.error(
                request,
                f"Impossible d'annuler cette réservation. "
                f"Statut actuel : {reservation.get_status_display()}.",
            )

        return redirect("reservations:reservation_list")

    def get(self, request, *args, **kwargs):
        """Cancel only accepts POST requests."""
        return HttpResponseNotAllowed(["POST"])


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


class AdminReservationListView(AdminRequiredMixin, ListView):
    """
    Admin reservation list: displays ALL reservations across all clients.

    Supports filtering by status via ?status= query parameter.
    Results are ordered by creation date descending (most recent first).

    Requirements: 12.2, 11.1, 11.2, 11.3, 11.4
    """

    model = Reservation
    template_name = "reservations/admin_list.html"
    context_object_name = "reservations"
    paginate_by = 20

    def get_queryset(self):
        queryset = Reservation.objects.select_related(
            "client", "pet", "service"
        ).all()
        status_filter = self.request.GET.get("status")
        if status_filter and status_filter in dict(Reservation.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Reservation.STATUS_CHOICES
        context["current_status"] = self.request.GET.get("status", "")
        return context


class ReservationApproveView(AdminRequiredMixin, View):
    """
    Admin action: approve a pending reservation.

    POST only. Calls reservation.transition_to("approved").
    Handles ValueError if the transition is not allowed.

    Requirements: 11.1
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        try:
            reservation.transition_to("approved")
            messages.success(
                request,
                f"La réservation #{reservation.pk} a été approuvée.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("admin_reservations:admin_list")


class ReservationRejectView(AdminRequiredMixin, View):
    """
    Admin action: reject a pending reservation.

    POST only. Calls reservation.transition_to("rejected").
    Handles ValueError if the transition is not allowed.

    Requirements: 11.2
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        try:
            reservation.transition_to("rejected")
            messages.success(
                request,
                f"La réservation #{reservation.pk} a été rejetée.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("admin_reservations:admin_list")


class ReservationCompleteView(AdminRequiredMixin, View):
    """
    Admin action: mark an approved reservation as completed.

    POST only. Calls reservation.transition_to("completed").
    Handles ValueError if the transition is not allowed.

    Requirements: 11.3
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        try:
            reservation.transition_to("completed")
            messages.success(
                request,
                f"La réservation #{reservation.pk} a été marquée comme terminée.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("admin_reservations:admin_list")
