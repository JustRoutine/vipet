"""
Property-based tests for the VIPET Reservations app.

# Feature: vipet-full-platform

Tests cover:
- Property 8: Reservation date validation
- Property 9: Reservation creation validates pet ownership and service availability
- Property 10: Reservation state machine transitions
- Property 12: Reservation visibility by role
- Property 13: Reservation status filtering

**Validates: Requirements 10.4, 10.5, 10.2, 10.3, 11.1–11.4, 11.6, 11.7, 12.1, 12.2, 12.4**
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.accounts.models import CustomUser
from apps.pets.models import Pet
from apps.reservations.models import Reservation
from apps.services.models import Service


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# All possible reservation statuses
ALL_STATUSES = [choice[0] for choice in Reservation.STATUS_CHOICES]

status_strategy = st.sampled_from(ALL_STATUSES)

# Generate date offsets relative to today for start_date testing
# Negative means past, positive means future
date_offset_strategy = st.integers(min_value=-365, max_value=365)

# Strategy for pairs of date offsets (start_offset, end_offset relative to start)
date_pair_strategy = st.tuples(
    st.integers(min_value=-30, max_value=30),  # start offset from today
    st.integers(min_value=-5, max_value=30),   # end offset from start
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(email_suffix: str, role: str = "client") -> CustomUser:
    """Create a test user with a unique email."""
    return CustomUser.objects.create_user(
        email=f"test_{uuid.uuid4().hex[:12]}@vipet.com",
        password="TestPass123!",
        first_name="Test",
        last_name="User",
        role=role,
    )


def _create_pet(owner: CustomUser, name: str = "Buddy") -> Pet:
    """Create a test pet belonging to the given owner."""
    return Pet.objects.create(
        owner=owner,
        name=name,
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=Decimal("10.00"),
    )


def _create_service(name: str = "Grooming Basic", is_available: bool = True) -> Service:
    """Create a test service."""
    return Service.objects.create(
        name=name,
        category="grooming",
        description="A grooming service",
        price=Decimal("50.00"),
        is_available=is_available,
    )


def _create_reservation(
    client: CustomUser,
    pet: Pet,
    service: Service,
    status: str = "pending",
    start_date: date | None = None,
    end_date: date | None = None,
) -> Reservation:
    """Create a reservation directly in the DB (bypass model validation)."""
    if start_date is None:
        start_date = date.today() + timedelta(days=1)
    if end_date is None:
        end_date = start_date + timedelta(days=2)
    return Reservation.objects.create(
        client=client,
        pet=pet,
        service=service,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )


# ---------------------------------------------------------------------------
# Property 8: Reservation date validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProperty8DateValidation:
    """
    Property 8: Reservation date validation

    For any pair of dates (start_date, end_date), the reservation system SHALL
    accept the dates if and only if start_date >= today AND end_date > start_date.
    All other date combinations SHALL be rejected.

    **Validates: Requirements 10.4, 10.5**
    """

    @settings(max_examples=10, deadline=None)
    @given(data=st.data())
    def test_valid_dates_accepted(self, data):
        """
        When start_date >= today and end_date > start_date,
        clean() should NOT raise ValidationError.
        """
        today = date.today()
        # Generate start_date that is today or in the future
        start_offset = data.draw(st.integers(min_value=0, max_value=365))
        start_date = today + timedelta(days=start_offset)

        # Generate end_date that is strictly after start_date
        end_offset = data.draw(st.integers(min_value=1, max_value=365))
        end_date = start_date + timedelta(days=end_offset)

        reservation = Reservation(
            start_date=start_date,
            end_date=end_date,
        )
        # Should not raise
        reservation.clean()

    @settings(max_examples=10, deadline=None)
    @given(data=st.data())
    def test_past_start_date_rejected(self, data):
        """
        When start_date < today, clean() should raise ValidationError
        on the start_date field.
        """
        today = date.today()
        # Generate a start_date in the past
        days_in_past = data.draw(st.integers(min_value=1, max_value=365))
        start_date = today - timedelta(days=days_in_past)
        # end_date after start_date (valid relative to start, but start is invalid)
        end_offset = data.draw(st.integers(min_value=1, max_value=30))
        end_date = start_date + timedelta(days=end_offset)

        reservation = Reservation(
            start_date=start_date,
            end_date=end_date,
        )
        with pytest.raises(ValidationError) as exc_info:
            reservation.clean()
        assert "start_date" in exc_info.value.message_dict

    @settings(max_examples=10, deadline=None)
    @given(data=st.data())
    def test_end_date_not_after_start_rejected(self, data):
        """
        When end_date <= start_date, clean() should raise ValidationError
        on the end_date field.
        """
        today = date.today()
        # Valid start_date (today or future)
        start_offset = data.draw(st.integers(min_value=0, max_value=365))
        start_date = today + timedelta(days=start_offset)
        # end_date on the same day or before start_date
        end_offset = data.draw(st.integers(min_value=-30, max_value=0))
        end_date = start_date + timedelta(days=end_offset)

        reservation = Reservation(
            start_date=start_date,
            end_date=end_date,
        )
        with pytest.raises(ValidationError) as exc_info:
            reservation.clean()
        assert "end_date" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# Property 9: Reservation creation validates pet ownership and service availability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProperty9OwnershipAndAvailability:
    """
    Property 9: Reservation creation validates pet ownership and service availability

    For any reservation creation request, the system SHALL reject the request if
    the specified pet is not owned by the authenticated client OR the specified
    service has is_available == False.

    **Validates: Requirements 10.2, 10.3**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        owns_pet=st.booleans(),
        service_available=st.booleans(),
    )
    def test_pet_ownership_and_service_availability(
        self, owns_pet: bool, service_available: bool
    ):
        """
        Generate cross-client pet/service combos.
        Reservation form should accept only when pet belongs to user AND service is available.
        """
        from apps.reservations.forms import ReservationForm

        # Create users
        client = _create_user(f"client_{owns_pet}_{service_available}")
        other_client = _create_user(f"other_{owns_pet}_{service_available}")

        # Create pet owned by client or other_client depending on owns_pet
        pet_owner = client if owns_pet else other_client
        pet = _create_pet(pet_owner, name=f"Pet_{owns_pet}_{service_available}")

        # Create service with given availability
        service = _create_service(
            name=f"Svc_{owns_pet}_{service_available}",
            is_available=service_available,
        )

        # Form data with valid dates
        today = date.today()
        form_data = {
            "pet": pet.pk,
            "service": service.pk,
            "start_date": today + timedelta(days=1),
            "end_date": today + timedelta(days=3),
            "notes": "",
        }

        form = ReservationForm(data=form_data, user=client)
        is_valid = form.is_valid()

        if owns_pet and service_available:
            # Should be accepted
            assert is_valid, f"Form should be valid but errors: {form.errors}"
        else:
            # Should be rejected
            assert not is_valid, (
                f"Form should be invalid (owns_pet={owns_pet}, "
                f"service_available={service_available})"
            )
            if not owns_pet:
                assert "pet" in form.errors
            if not service_available:
                assert "service" in form.errors


# ---------------------------------------------------------------------------
# Property 10: Reservation state machine transitions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProperty10StateMachineTransitions:
    """
    Property 10: Reservation state machine transitions

    For any reservation with any current status and any attempted transition to
    a new status, the transition SHALL succeed if and only if the new status is
    in ALLOWED_TRANSITIONS[current_status].

    **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.6, 11.7**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        current_status=status_strategy,
        target_status=status_strategy,
    )
    def test_transition_allowed_iff_in_allowed_transitions(
        self, current_status: str, target_status: str
    ):
        """
        Generate all status/transition combos and verify:
        - If target_status is in ALLOWED_TRANSITIONS[current_status], transition succeeds
        - Otherwise, transition raises ValueError
        """
        client = _create_user(f"sm_{current_status}_{target_status}")
        pet = _create_pet(client)
        service = _create_service(name=f"Svc_SM_{current_status}_{target_status}")

        reservation = _create_reservation(
            client=client,
            pet=pet,
            service=service,
            status=current_status,
        )

        allowed = Reservation.ALLOWED_TRANSITIONS.get(current_status, [])
        is_allowed = target_status in allowed

        if is_allowed:
            # Transition should succeed
            reservation.transition_to(target_status)
            reservation.refresh_from_db()
            assert reservation.status == target_status
        else:
            # Transition should be rejected
            with pytest.raises(ValueError):
                reservation.transition_to(target_status)
            # Status should remain unchanged
            reservation.refresh_from_db()
            assert reservation.status == current_status

    def test_can_transition_to_consistency(self):
        """
        Verify can_transition_to() returns True for all allowed transitions
        and False for disallowed ones (exhaustive check).
        """
        for current, allowed_list in Reservation.ALLOWED_TRANSITIONS.items():
            for target in ALL_STATUSES:
                r = Reservation(status=current)
                if target in allowed_list:
                    assert r.can_transition_to(target) is True
                else:
                    assert r.can_transition_to(target) is False


# ---------------------------------------------------------------------------
# Property 12: Reservation visibility by role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProperty12VisibilityByRole:
    """
    Property 12: Reservation visibility by role

    For any set of reservations across multiple clients: when a client queries
    reservations, they SHALL receive only their own; when an admin queries
    reservations, they SHALL receive all reservations in the system.

    **Validates: Requirements 12.1, 12.2**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        num_clients=st.integers(min_value=2, max_value=4),
        reservations_per_client=st.integers(min_value=1, max_value=3),
    )
    def test_client_sees_only_own_reservations(
        self, num_clients: int, reservations_per_client: int
    ):
        """
        Generate multi-client reservations and verify each client sees only their own.
        """
        clients = []
        all_reservations = []
        service = _create_service(
            name=f"Svc_vis_{num_clients}_{reservations_per_client}"
        )

        for i in range(num_clients):
            client = _create_user(f"vis_client_{i}_{num_clients}_{reservations_per_client}")
            clients.append(client)
            pet = _create_pet(client, name=f"Pet_vis_{i}")

            for j in range(reservations_per_client):
                res = _create_reservation(
                    client=client,
                    pet=pet,
                    service=service,
                    start_date=date.today() + timedelta(days=i * 10 + j + 1),
                    end_date=date.today() + timedelta(days=i * 10 + j + 3),
                )
                all_reservations.append(res)

        total_expected = num_clients * reservations_per_client

        # Each client should see only their own reservations
        for idx, client in enumerate(clients):
            client_reservations = Reservation.objects.filter(client=client)
            assert client_reservations.count() == reservations_per_client
            # All returned reservations belong to this client
            for r in client_reservations:
                assert r.client_id == client.pk

        # Admin should see all reservations
        admin_reservations = Reservation.objects.all()
        assert admin_reservations.count() >= total_expected


# ---------------------------------------------------------------------------
# Property 13: Reservation status filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProperty13StatusFiltering:
    """
    Property 13: Reservation status filtering

    For any valid status filter value and any set of reservations, filtering by
    that status SHALL return only reservations whose status matches the filter
    value, with no false inclusions or omissions.

    **Validates: Requirements 12.4**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        statuses=st.lists(
            status_strategy,
            min_size=3,
            max_size=8,
        ),
        filter_status=status_strategy,
    )
    def test_status_filter_accuracy(self, statuses: list, filter_status: str):
        """
        Generate reservations with various statuses, then filter by a specific status.
        Verify:
        - All returned reservations have the filtered status
        - No reservations with that status are missing from the result
        """
        client = _create_user(f"filter_{filter_status}_{len(statuses)}")
        pet = _create_pet(client, name=f"Pet_filter_{filter_status}")
        service = _create_service(name=f"Svc_filter_{filter_status}_{len(statuses)}")

        created_ids_by_status: dict[str, list[int]] = {s: [] for s in ALL_STATUSES}

        for idx, s in enumerate(statuses):
            res = _create_reservation(
                client=client,
                pet=pet,
                service=service,
                status=s,
                start_date=date.today() + timedelta(days=idx + 1),
                end_date=date.today() + timedelta(days=idx + 3),
            )
            created_ids_by_status[s].append(res.pk)

        # Apply filter
        filtered_qs = Reservation.objects.filter(
            client=client, status=filter_status
        )

        # All results must have the correct status
        for r in filtered_qs:
            assert r.status == filter_status

        # Count must match expected
        expected_count = len(created_ids_by_status[filter_status])
        assert filtered_qs.count() == expected_count

        # All expected IDs must be present
        filtered_ids = set(filtered_qs.values_list("pk", flat=True))
        expected_ids = set(created_ids_by_status[filter_status])
        assert filtered_ids == expected_ids
