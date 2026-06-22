"""
Service API views for the VIPET REST API.

Provides a public read-only endpoint to list available services with optional
filtering by category and availability. Admin users can create, update, and
delete services.

Requirements: 8.6, 9.5, 9.6, 9.7, 21.1, 21.2, 21.6
"""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.core.permissions import IsAdmin
from apps.services.models import Service
from apps.services.serializers import ServiceSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, creating, updating, and deleting services.

    - Public read access (no authentication required for list/retrieve).
    - Admin-only write access (create, update, partial_update, destroy).
    - By default returns only available services (is_available=True).
    - Supports filtering via query parameters:
        - `category`: filter by exact category value (one of the 7 defined categories)
        - `available`: set to "false" to include unavailable services; defaults to showing only available
    """

    serializer_class = ServiceSerializer

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.

        - list, retrieve: public access (AllowAny)
        - create, update, partial_update, destroy: admin only
        """
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        """
        Return services queryset with optional filtering.

        Query parameters:
            category (str): Filter by category value (e.g. "grooming", "spa").
            available (str): If "false", include all services regardless of availability.
                             By default, only available services are returned.
        """
        queryset = Service.objects.all()

        # By default, only show available services (Requirement 9.5)
        available_param = self.request.query_params.get("available", "").lower()
        if available_param != "false":
            queryset = queryset.filter(is_available=True)

        # Filter by category if provided (Requirement 9.5, 9.7)
        category = self.request.query_params.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)

        return queryset.order_by("name")
