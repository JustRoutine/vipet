"""
Notification serializers for the VIPET REST API.

Requirements: 13.2, 13.5
"""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Notification records.

    Fields: id, message, is_read, created_at.
    All fields are read-only since notifications are system-generated.
    """

    class Meta:
        model = Notification
        fields = ["id", "message", "is_read", "created_at"]
        read_only_fields = ["id", "message", "is_read", "created_at"]
