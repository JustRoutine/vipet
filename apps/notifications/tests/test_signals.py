"""
Unit tests for notification signal handlers.

Tests that reservation status changes trigger notification creation
with the correct message content.

Requirements: 11.5, 13.1, 10.7
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.accounts.models import CustomUser
from apps.notifications.models import Notification
from apps.pets.models import Pet
from apps.reservations.models import Reservation
from apps.services.models import Service


@pytest.mark.django_db
class TestStatusChangeNotificationSignal(TestCase):
    """Tests for the post_save signal that creates notifications on status change."""

    def setUp(self):
        self.client_user = CustomUser.objects.create_user(
            email="client@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            role="client",
        )
        self.pet = Pet.objects.create(
            owner=self.client_user,
            name="Buddy",
            species="dog",
            gender="male",
            date_of_birth=date(2020, 1, 1),
            weight=Decimal("15.00"),
        )
        self.service = Service.objects.create(
            name="Grooming",
            category="grooming",
            description="Premium grooming service",
            price=Decimal("100.00"),
            is_available=True,
        )
        self.reservation = Reservation.objects.create(
            client=self.client_user,
            pet=self.pet,
            service=self.service,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            status="pending",
        )

    def test_no_notification_on_creation(self):
        """No notification should be created when a reservation is first created."""
        # The reservation was created in setUp with status 'pending'
        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 0

    def test_notification_on_status_change_to_approved(self):
        """Notification created when status changes from pending to approved."""
        self.reservation.transition_to("approved")

        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 1

        notification = notifications.first()
        assert "Buddy" in notification.message
        assert "Grooming" in notification.message
        assert "approved" in notification.message

    def test_notification_on_status_change_to_rejected(self):
        """Notification created when status changes from pending to rejected."""
        self.reservation.transition_to("rejected")

        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 1

        notification = notifications.first()
        assert "Buddy" in notification.message
        assert "Grooming" in notification.message
        assert "rejected" in notification.message

    def test_notification_on_status_change_to_cancelled(self):
        """Notification created when status changes from pending to cancelled."""
        self.reservation.transition_to("cancelled")

        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 1

        notification = notifications.first()
        assert "Buddy" in notification.message
        assert "Grooming" in notification.message
        assert "cancelled" in notification.message

    def test_notification_on_status_change_to_completed(self):
        """Notification created when status changes from approved to completed."""
        self.reservation.transition_to("approved")
        # Clear the approval notification
        Notification.objects.all().delete()

        self.reservation.transition_to("completed")

        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 1

        notification = notifications.first()
        assert "Buddy" in notification.message
        assert "Grooming" in notification.message
        assert "completed" in notification.message

    def test_no_notification_on_save_without_status_change(self):
        """No notification when saving without changing status."""
        self.reservation.notes = "Updated notes"
        self.reservation.save()

        notifications = Notification.objects.filter(user=self.client_user)
        assert notifications.count() == 0

    def test_notification_message_format(self):
        """Notification message follows the expected format."""
        self.reservation.transition_to("approved")

        notification = Notification.objects.get(user=self.client_user)
        expected = "Your reservation for Buddy (Grooming) has been approved."
        assert notification.message == expected

    def test_notification_linked_to_correct_user(self):
        """Notification is linked to the reservation's client, not other users."""
        other_user = CustomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Jane",
            last_name="Smith",
            role="client",
        )

        self.reservation.transition_to("approved")

        assert Notification.objects.filter(user=self.client_user).count() == 1
        assert Notification.objects.filter(user=other_user).count() == 0

    def test_notification_is_unread_by_default(self):
        """Newly created notification has is_read=False."""
        self.reservation.transition_to("approved")

        notification = Notification.objects.get(user=self.client_user)
        assert notification.is_read is False
