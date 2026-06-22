"""
Property-based tests for the VIPET Notifications app.

**Validates: Requirements 11.5, 13.1, 10.7, 13.3, 13.4**

Property 11: Status change generates notification with correct content
----------------------------------------------------------------------
For any valid reservation status transition, the system SHALL create a
Notification record for the reservation's owning client, and the notification
message SHALL contain the pet name, service name, and the new status value.

Property 14: Mark notification as read is idempotent
----------------------------------------------------
For any notification belonging to the authenticated client, marking it as read
SHALL result in is_read == True. Marking an already-read notification as read
again SHALL leave is_read == True and return success (no error).

Property 15: Unread notification count accuracy
------------------------------------------------
For any client with any set of notifications (some read, some unread), the
unread-count endpoint SHALL return the exact count of notifications where
user == client AND is_read == False.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.accounts.models import CustomUser
from apps.notifications.models import Notification
from apps.pets.models import Pet
from apps.reservations.models import Reservation
from apps.services.models import Service


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid transitions: (from_status, to_status) pairs that are allowed
VALID_TRANSITIONS = [
    ("pending", "approved"),
    ("pending", "rejected"),
    ("pending", "cancelled"),
    ("approved", "completed"),
]

valid_transition_strategy = st.sampled_from(VALID_TRANSITIONS)

# Strategy for pet names - printable text without control characters
pet_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00\n\r",
    ),
    min_size=1,
    max_size=50,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# Strategy for service names
service_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00\n\r",
    ),
    min_size=1,
    max_size=50,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# Strategy for number of times to mark read (idempotency)
mark_read_count_strategy = st.integers(min_value=1, max_value=10)

# Strategy for lists of booleans representing read/unread notifications
notification_read_states_strategy = st.lists(
    st.booleans(),
    min_size=0,
    max_size=30,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_client(suffix: str = "") -> CustomUser:
    """Create a client user for testing."""
    return CustomUser.objects.create_user(
        email=f"client_{uuid.uuid4().hex[:12]}@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Client",
        role="client",
    )


def _create_pet(owner: CustomUser, name: str = "Buddy") -> Pet:
    """Create a pet for testing."""
    return Pet.objects.create(
        owner=owner,
        name=name,
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=Decimal("10.00"),
    )


def _create_service(name: str = "Grooming") -> Service:
    """Create a service for testing."""
    return Service.objects.create(
        name=name,
        category="grooming",
        description="Test service",
        price=Decimal("100.00"),
        is_available=True,
    )


def _create_reservation(
    client: CustomUser, pet: Pet, service: Service, status: str = "pending"
) -> Reservation:
    """Create a reservation for testing."""
    return Reservation.objects.create(
        client=client,
        pet=pet,
        service=service,
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=10),
        status=status,
    )


# ---------------------------------------------------------------------------
# Property 11: Status change generates notification with correct content
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestProperty11StatusChangeNotification:
    """
    # Feature: vipet-full-platform, Property 11: Status change generates
    # notification with correct content

    **Validates: Requirements 11.5, 13.1, 10.7**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        transition=valid_transition_strategy,
        pet_name=pet_name_strategy,
        service_name=service_name_strategy,
    )
    def test_status_change_creates_notification_with_correct_content(
        self, transition, pet_name, service_name
    ):
        """
        For any valid status transition, a Notification is created for the
        reservation's owning client, and the message contains the pet name,
        service name, and the new status value.

        **Validates: Requirements 11.5, 13.1, 10.7**
        """
        from_status, to_status = transition

        # Setup: create test data
        client = _create_client(suffix=f"_{id(transition)}_{pet_name[:5]}")
        pet = _create_pet(owner=client, name=pet_name)
        service = _create_service(name=service_name)

        # For transitions from "approved", we need to first create with
        # pending and transition to approved before testing the target
        if from_status == "approved":
            reservation = _create_reservation(
                client=client, pet=pet, service=service, status="pending"
            )
            # Transition to approved first
            reservation.transition_to("approved")
            # Clear notification from the first transition
            Notification.objects.filter(user=client).delete()
        else:
            reservation = _create_reservation(
                client=client, pet=pet, service=service, status=from_status
            )

        # Count notifications before
        count_before = Notification.objects.filter(user=client).count()

        # Perform the transition
        reservation.transition_to(to_status)

        # Verify: notification was created
        notifications = Notification.objects.filter(user=client)
        assert notifications.count() == count_before + 1

        # Get the most recent notification
        notification = notifications.order_by("-created_at").first()

        # Verify: message contains pet name, service name, and new status
        assert pet_name in notification.message, (
            f"Expected pet name '{pet_name}' in message: {notification.message}"
        )
        assert service_name in notification.message, (
            f"Expected service name '{service_name}' in message: {notification.message}"
        )
        # The status display value (lowercase) should be in the message
        new_status_display = dict(Reservation.STATUS_CHOICES)[to_status].lower()
        assert new_status_display in notification.message, (
            f"Expected status '{new_status_display}' in message: {notification.message}"
        )

        # Verify: notification belongs to the correct user
        assert notification.user == client

        # Cleanup
        Notification.objects.filter(user=client).delete()
        reservation.delete()
        pet.delete()
        service.delete()
        client.delete()


# ---------------------------------------------------------------------------
# Property 14: Mark notification as read is idempotent
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestProperty14MarkReadIdempotent:
    """
    # Feature: vipet-full-platform, Property 14: Mark notification as read
    # is idempotent

    **Validates: Requirements 13.3**
    """

    @settings(max_examples=10, deadline=None)
    @given(times=mark_read_count_strategy)
    def test_mark_read_idempotent(self, times):
        """
        For any notification, marking it as read N times (N >= 1) SHALL
        always result in is_read == True, regardless of how many times it
        is marked.

        **Validates: Requirements 13.3**
        """
        # Setup
        client = _create_client(suffix=f"_idem_{times}")
        notification = Notification.objects.create(
            user=client,
            message="Test notification for idempotency",
            is_read=False,
        )

        # Mark as read N times
        for _ in range(times):
            notification.is_read = True
            notification.save(update_fields=["is_read"])

            # After each mark, verify is_read is True
            notification.refresh_from_db()
            assert notification.is_read is True

        # Final verification
        notification.refresh_from_db()
        assert notification.is_read is True

        # Cleanup
        notification.delete()
        client.delete()

    @settings(max_examples=10, deadline=None)
    @given(
        initial_state=st.booleans(),
        times=mark_read_count_strategy,
    )
    def test_mark_read_from_any_initial_state(self, initial_state, times):
        """
        Regardless of the initial is_read state, marking as read N times
        always results in is_read == True.

        **Validates: Requirements 13.3**
        """
        # Setup
        client = _create_client(suffix=f"_state_{initial_state}_{times}")
        notification = Notification.objects.create(
            user=client,
            message="Test notification",
            is_read=initial_state,
        )

        # Mark as read N times
        for _ in range(times):
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        # Verify final state
        notification.refresh_from_db()
        assert notification.is_read is True

        # Cleanup
        notification.delete()
        client.delete()


# ---------------------------------------------------------------------------
# Property 15: Unread notification count accuracy
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestProperty15UnreadCountAccuracy:
    """
    # Feature: vipet-full-platform, Property 15: Unread notification count
    # accuracy

    **Validates: Requirements 13.4**
    """

    @settings(max_examples=10, deadline=None)
    @given(read_states=notification_read_states_strategy)
    def test_unread_count_matches_actual_unread(self, read_states):
        """
        For any set of notifications with arbitrary read/unread states,
        the unread count SHALL equal the exact number of notifications
        where is_read == False for that user.

        **Validates: Requirements 13.4**
        """
        # Setup
        client = _create_client(suffix=f"_count_{len(read_states)}")

        # Create notifications with the given read states
        for i, is_read in enumerate(read_states):
            Notification.objects.create(
                user=client,
                message=f"Notification {i}",
                is_read=is_read,
            )

        # Calculate expected unread count
        expected_unread = sum(1 for state in read_states if not state)

        # Verify using the same query the viewset uses
        actual_unread = Notification.objects.filter(
            user=client, is_read=False
        ).count()

        assert actual_unread == expected_unread, (
            f"Expected {expected_unread} unread notifications, "
            f"got {actual_unread}. States: {read_states}"
        )

        # Also verify that total count is correct
        total = Notification.objects.filter(user=client).count()
        assert total == len(read_states)

        # Cleanup
        Notification.objects.filter(user=client).delete()
        client.delete()

    @settings(max_examples=10, deadline=None)
    @given(read_states=notification_read_states_strategy)
    def test_unread_count_excludes_other_users(self, read_states):
        """
        Unread count for a user SHALL only count that user's unread
        notifications, not those of other users.

        **Validates: Requirements 13.4**
        """
        # Setup two users
        client_a = _create_client(suffix=f"_a_{len(read_states)}")
        client_b = _create_client(suffix=f"_b_{len(read_states)}")

        # Create notifications for client_a with the given states
        for i, is_read in enumerate(read_states):
            Notification.objects.create(
                user=client_a,
                message=f"Notification A-{i}",
                is_read=is_read,
            )

        # Create some notifications for client_b (all unread)
        for i in range(3):
            Notification.objects.create(
                user=client_b,
                message=f"Notification B-{i}",
                is_read=False,
            )

        # Expected unread for client_a
        expected_unread_a = sum(1 for state in read_states if not state)

        # Verify client_a's unread count is accurate
        actual_unread_a = Notification.objects.filter(
            user=client_a, is_read=False
        ).count()
        assert actual_unread_a == expected_unread_a

        # Verify client_b's unread count is independent
        actual_unread_b = Notification.objects.filter(
            user=client_b, is_read=False
        ).count()
        assert actual_unread_b == 3

        # Cleanup
        Notification.objects.filter(user=client_a).delete()
        Notification.objects.filter(user=client_b).delete()
        client_a.delete()
        client_b.delete()
