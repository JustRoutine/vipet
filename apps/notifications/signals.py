"""
Signal handlers for the notifications app.

Creates notifications when reservation statuses change.

Requirements: 11.5, 13.1, 10.7
"""

from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from apps.reservations.models import Reservation

from .models import Notification


@receiver(post_init, sender=Reservation)
def store_original_status(instance: Reservation, **kwargs) -> None:
    """Store the original status when a Reservation instance is loaded."""
    instance._original_status = instance.status


@receiver(post_save, sender=Reservation)
def create_status_change_notification(
    instance: Reservation, created: bool, **kwargs
) -> None:
    """
    Create a notification when a reservation's status changes.

    Skips notification on initial creation (status is 'pending').
    Only fires when the status has actually changed from its original value.
    """
    if created:
        return

    original_status = getattr(instance, "_original_status", None)

    if original_status is None or original_status == instance.status:
        return

    pet_name = instance.pet.name
    service_name = instance.service.name
    new_status_display = instance.get_status_display().lower()

    message = (
        f"Your reservation for {pet_name} ({service_name}) "
        f"has been {new_status_display}."
    )

    Notification.objects.create(
        user=instance.client,
        message=message,
    )

    # Update the stored status so subsequent saves don't re-trigger
    instance._original_status = instance.status
