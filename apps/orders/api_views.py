"""
Order API views for the VIPET REST API.

Provides read-only endpoints for clients to view their order history:
  - GET /api/v1/orders/       → List client's orders (paginated, 20/page)
  - GET /api/v1/orders/{id}/  → Order detail with items

Requirements: 8.1, 8.2, 8.3, 8.5
"""

from rest_framework import permissions, viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.core.pagination import StandardResultsSetPagination
from apps.core.permissions import IsClient
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer


class OrderViewSet(ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only ViewSet for client order history.

    - List: paginated (20/page), sorted by -created_at, filtered to
      the authenticated client only.
    - Retrieve: single order detail with nested OrderItems.

    If the client has no orders, list returns an empty page (Req 8.5).

    Requirements: 8.1, 8.2, 8.3, 8.5
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsClient]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Return only orders belonging to the authenticated client,
        sorted by most recent first. Prefetch items for efficiency.

        Requirements: 8.2 (client isolation)
        """
        return (
            Order.objects.filter(client=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )
