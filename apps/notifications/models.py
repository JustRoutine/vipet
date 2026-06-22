"""
Notification model for the VIPET notifications app.

Requirements: 13.1, 13.3, 13.4
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Stores notification records for clients.

    Notifications are auto-generated when reservation statuses change,
    informing clients about their booking updates.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "-created_at"],
                name="notif_user_read_idx",
            ),
        ]

    def __str__(self) -> str:
        read_status = "read" if self.is_read else "unread"
        return f"Notification for {self.user} ({read_status})"
