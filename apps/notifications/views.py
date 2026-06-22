"""
Notification API viewset for the VIPET notifications app.

Provides:
  - List notifications (paginated, filtered by authenticated user)
  - Mark a notification as read (PATCH, idempotent)
  - Get unread notification count (GET)

Requirements: 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.core.permissions import IsOwner
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationPagination(PageNumberPagination):
    """Pagination for notification list: max 50 per page."""

    page_size = 50


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API viewset for Notification resources.

    - Requires JWT authentication.
    - Queryset is filtered to only return notifications belonging to
      the authenticated user (ownership enforcement via queryset).
    - Object-level ownership is additionally enforced via IsOwner permission.
    - Ordered by created_at descending (newest first).
    - Paginated with a max page size of 50.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    pagination_class = NotificationPagination

    def get_queryset(self):
        """Return only notifications belonging to the authenticated user."""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        """
        Mark a single notification as read.

        Idempotent: if the notification is already read, it remains read
        and a success response is returned.

        Requirements: 13.3, 13.6, 13.7
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """
        Return the count of unread notifications for the authenticated user.

        Requirements: 13.4
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count}, status=status.HTTP_200_OK)
