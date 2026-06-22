"""
Notification API URL configuration.

DRF router providing (under /api/v1/notifications/):
  GET    /                    → list notifications (paginated, user-filtered)
  GET    /{id}/               → notification detail
  PATCH  /{id}/read/          → mark notification as read
  GET    /unread-count/       → count of unread notifications

Requirements: 13.5
"""

from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationViewSet

app_name = "notifications"

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = router.urls
