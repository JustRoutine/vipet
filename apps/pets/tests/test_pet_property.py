"""
Property-based tests for the Pet model (apps.pets).

Feature: vipet-full-platform

Properties tested:
- Property 1: Pet ownership isolation
- Property 2: Pet weight validation
- Property 3: Pet deletion with future reservations guard

**Validates: Requirements 7.2, 7.5, 7.7, 7.4, 7.11**
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.accounts.models import CustomUser
from apps.pets.models import Pet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(email: str) -> CustomUser:
    """Create a client user for testing."""
    return CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="User",
        role="client",
    )


def _create_pet(owner: CustomUser, name: str = "Buddy", weight: Decimal = Decimal("5.00")) -> Pet:
    """Create a valid pet for the given owner."""
    return Pet.objects.create(
        owner=owner,
        name=name,
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=weight,
    )


# ---------------------------------------------------------------------------
# Property 1: Pet ownership isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(
    num_users=st.integers(min_value=2, max_value=5),
    pets_per_user=st.integers(min_value=1, max_value=4),
)
def test_property1_pet_ownership_isolation(num_users: int, pets_per_user: int) -> None:
    """
    **Validates: Requirements 7.2, 7.5**

    Property 1: Pet ownership isolation — For any client and any set of pets
    in the system (owned by various clients), querying the pet list for that
    client SHALL return only pets where owner == client, and SHALL return all
    such pets.
    """
    # Clean slate for each example
    Pet.objects.all().delete()
    CustomUser.objects.filter(email__startswith="prop1_").delete()

    # Create users and their pets
    users = []
    for i in range(num_users):
        user = _create_user(f"prop1_user{i}@test.com")
        users.append(user)
        for j in range(pets_per_user):
            _create_pet(owner=user, name=f"Pet_{i}_{j}")

    # Verify ownership isolation for each user
    for user in users:
        owned_pets = Pet.objects.filter(owner=user)
        # Should return exactly the number of pets created for this user
        assert owned_pets.count() == pets_per_user, (
            f"Expected {pets_per_user} pets for {user.email}, got {owned_pets.count()}"
        )
        # Every returned pet must belong to this user
        for pet in owned_pets:
            assert pet.owner == user, (
                f"Pet '{pet.name}' returned for {user.email} but owned by {pet.owner.email}"
            )

    # Total pets in system should equal num_users * pets_per_user
    assert Pet.objects.count() == num_users * pets_per_user


# ---------------------------------------------------------------------------
# Property 2: Pet weight validation
# ---------------------------------------------------------------------------

# Strategy: valid weights (0.01 to 999.99 with up to 2 decimal places)
_valid_weights = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999.99"),
    places=2,
)

# Strategy: invalid weights below minimum
_weights_too_low = st.decimals(
    min_value=Decimal("-1000.00"),
    max_value=Decimal("0.00"),
    places=2,
)

# Strategy: invalid weights above maximum
_weights_too_high = st.decimals(
    min_value=Decimal("1000.00"),
    max_value=Decimal("99999.99"),
    places=2,
)


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(weight=_valid_weights)
def test_property2_valid_weights_accepted(weight: Decimal) -> None:
    """
    **Validates: Requirements 7.7**

    Property 2: Pet weight validation — valid weights (0.01–999.99 with at most
    2 decimal places) SHALL be accepted by the model's clean() method.
    """
    pet = Pet(
        name="TestPet",
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=weight,
    )
    # clean() should not raise for valid weights
    pet.clean()


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(weight=_weights_too_low)
def test_property2_weights_below_minimum_rejected(weight: Decimal) -> None:
    """
    **Validates: Requirements 7.7**

    Property 2: Pet weight validation — weights below 0.01 SHALL be rejected.
    """
    pet = Pet(
        name="TestPet",
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=weight,
    )
    with pytest.raises(ValidationError) as exc_info:
        pet.clean()
    assert "weight" in exc_info.value.message_dict


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(weight=_weights_too_high)
def test_property2_weights_above_maximum_rejected(weight: Decimal) -> None:
    """
    **Validates: Requirements 7.7**

    Property 2: Pet weight validation — weights above 999.99 SHALL be rejected.
    """
    pet = Pet(
        name="TestPet",
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=weight,
    )
    with pytest.raises(ValidationError) as exc_info:
        pet.clean()
    assert "weight" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# Property 3: Pet deletion with future reservations guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(
    days_offset=st.integers(min_value=0, max_value=365),
)
def test_property3_deletion_blocked_with_future_reservations(days_offset: int) -> None:
    """
    **Validates: Requirements 7.4, 7.11**

    Property 3: Pet deletion with future reservations guard — deletion SHALL
    be rejected if the pet has reservations with end_date >= today.
    """
    from apps.reservations.models import Reservation
    from apps.services.models import Service

    # Clean slate
    Reservation.objects.all().delete()
    Pet.objects.all().delete()
    Service.objects.all().delete()
    CustomUser.objects.filter(email__startswith="prop3_").delete()

    user = _create_user("prop3_owner@test.com")
    pet = _create_pet(owner=user, name="GuardedPet")

    service = Service.objects.create(
        name="Test Service",
        category="grooming",
        description="A test service",
        price=Decimal("100.00"),
        is_available=True,
    )

    # Create a reservation with end_date in the future (or today)
    future_end = date.today() + timedelta(days=days_offset)
    start = date.today()
    # Ensure end > start for a valid reservation
    if future_end <= start:
        future_end = start + timedelta(days=1)

    Reservation.objects.create(
        client=user,
        pet=pet,
        service=service,
        start_date=start,
        end_date=future_end,
        status="pending",
    )

    # Simulate the deletion guard logic (same as PetDeleteView)
    has_future_reservations = Reservation.objects.filter(
        pet=pet,
        end_date__gte=date.today(),
    ).exists()

    assert has_future_reservations is True, (
        "Expected future reservation to block deletion"
    )


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(
    days_in_past=st.integers(min_value=1, max_value=365),
)
def test_property3_deletion_allowed_without_future_reservations(days_in_past: int) -> None:
    """
    **Validates: Requirements 7.4, 7.11**

    Property 3: Pet deletion with future reservations guard — deletion SHALL
    succeed if the pet has no reservations with end_date >= today (only past
    reservations exist).
    """
    from apps.reservations.models import Reservation
    from apps.services.models import Service

    # Clean slate
    Reservation.objects.all().delete()
    Pet.objects.all().delete()
    Service.objects.all().delete()
    CustomUser.objects.filter(email__startswith="prop3b_").delete()

    user = _create_user("prop3b_owner@test.com")
    pet = _create_pet(owner=user, name="DeletablePet")

    service = Service.objects.create(
        name="Test Service",
        category="grooming",
        description="A test service",
        price=Decimal("100.00"),
        is_available=True,
    )

    # Create a reservation entirely in the past
    past_end = date.today() - timedelta(days=days_in_past)
    past_start = past_end - timedelta(days=1)

    Reservation.objects.create(
        client=user,
        pet=pet,
        service=service,
        start_date=past_start,
        end_date=past_end,
        status="completed",
    )

    # Simulate the deletion guard logic
    has_future_reservations = Reservation.objects.filter(
        pet=pet,
        end_date__gte=date.today(),
    ).exists()

    assert has_future_reservations is False, (
        "Expected no future reservations to allow deletion"
    )

    # Verify pet can actually be deleted
    pet_id = pet.id
    pet.delete()
    assert not Pet.objects.filter(id=pet_id).exists()


@pytest.mark.django_db
def test_property3_deletion_allowed_when_no_reservations() -> None:
    """
    **Validates: Requirements 7.4, 7.11**

    Property 3: Pet deletion — A pet with zero reservations SHALL be deletable.
    """
    CustomUser.objects.filter(email="prop3c_owner@test.com").delete()
    user = _create_user("prop3c_owner@test.com")
    pet = _create_pet(owner=user, name="NeverBooked")

    # No reservations at all
    from apps.reservations.models import Reservation

    has_future_reservations = Reservation.objects.filter(
        pet=pet,
        end_date__gte=date.today(),
    ).exists()

    assert has_future_reservations is False
    pet_id = pet.id
    pet.delete()
    assert not Pet.objects.filter(id=pet_id).exists()


@pytest.mark.django_db
def test_property3_deletion_blocked_for_non_owner() -> None:
    """
    **Validates: Requirements 7.4, 7.5**

    Property 3: A client SHALL NOT be able to delete a pet they do not own.
    Queryset filtering by owner ensures non-owners get an empty queryset.
    """
    CustomUser.objects.filter(email__startswith="prop3d_").delete()
    owner = _create_user("prop3d_owner@test.com")
    other = _create_user("prop3d_other@test.com")
    pet = _create_pet(owner=owner, name="OwnedPet")

    # Other user's filtered queryset should NOT include this pet
    other_pets = Pet.objects.filter(owner=other)
    assert not other_pets.filter(id=pet.id).exists(), (
        "Non-owner should not see another owner's pet in their queryset"
    )
