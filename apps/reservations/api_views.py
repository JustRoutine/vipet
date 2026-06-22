"""
Reservation API viewset for the VIPET reservations app.

Provides list/create/retrieve actions with role-based queryset filtering,
and custom actions for status transitions (cancel, approve, reject, complete).

Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.6, 12.1, 12.2, 12.3,
              12.4, 12.5, 12.6, 21.1, 21.2
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdmin
from apps.reservations.models import Reservation
from apps.reservations.serializers import ReservationSerializer


class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Reservation resources.

    - Requires JWT authentication.
    - Role-based queryset:
        - Clients see only their own reservations.
        - Admins see all reservations.
    - Supports ?status= query parameter for filtering.
    - Only list, create, and retrieve actions are available (no update/delete).
    - Custom actions: cancel, approve, reject, complete.
    """

    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        """
        Return reservations based on the user's role.

        - Clients: only their own reservations.
        - Admins: all reservations.

        Supports filtering by ?status= query parameter.
        """
        user = self.request.user

        if user.role == "admin":
            queryset = Reservation.objects.select_related(
                "client", "pet", "service"
            ).all()
        else:
            queryset = Reservation.objects.select_related(
                "pet", "service"
            ).filter(client=user)

        # Status filtering
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter and status_filter in dict(Reservation.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)

        return queryset

    def perform_create(self, serializer):
        """Set the client to the currently authenticated user."""
        serializer.save(client=self.request.user)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Cancel a reservation.

        Client can cancel their own pending/approved reservations.
        Uses the model's transition_to() method for state enforcement.

        Requirements: 11.6, 11.7, 11.8
        """
        reservation = self.get_object()

        # Ownership check: clients can only cancel their own reservations
        if request.user.role != "admin" and reservation.client_id != request.user.pk:
            return Response(
                {"detail": "Vous n'avez pas la permission d'annuler cette réservation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            reservation.transition_to("cancelled")
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
        permission_classes=[permissions.IsAuthenticated, IsAdmin],
    )
    def approve(self, request, pk=None):
        """
        Approve a pending reservation (admin only).

        Calls transition_to("approved") which enforces valid transitions.

        Requirements: 11.1
        """
        reservation = self.get_object()

        try:
            reservation.transition_to("approved")
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[permissions.IsAuthenticated, IsAdmin],
    )
    def reject(self, request, pk=None):
        """
        Reject a pending reservation (admin only).

        Calls transition_to("rejected") which enforces valid transitions.

        Requirements: 11.2
        """
        reservation = self.get_object()

        try:
            reservation.transition_to("rejected")
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
        permission_classes=[permissions.IsAuthenticated, IsAdmin],
    )
    def complete(self, request, pk=None):
        """
        Complete an approved reservation (admin only).

        Calls transition_to("completed") which enforces valid transitions.

        Requirements: 11.3
        """
        reservation = self.get_object()

        try:
            reservation.transition_to("completed")
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data)
