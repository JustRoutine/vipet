"""
Unit tests for CartValidator (apps.cart.validators).

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.accounts.models import CustomUser
from apps.cart.models import Cart, CartItem
from apps.cart.validators import CartValidator
from apps.pets.models import Pet
from apps.services.models import Service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_user(db):
    """Create a client user."""
    return CustomUser.objects.create_user(
        email="client@vipet.com",
        password="TestPass123!",
        first_name="Test",
        last_name="Client",
        role="client",
    )


@pytest.fixture
def other_user(db):
    """Create another client user (for pet ownership tests)."""
    return CustomUser.objects.create_user(
        email="other@vipet.com",
        password="TestPass123!",
        first_name="Other",
        last_name="User",
        role="client",
    )


@pytest.fixture
def service(db):
    """Create an available service."""
    return Service.objects.create(
        name="Grooming",
        category="grooming",
        description="A grooming service",
        price=Decimal("100.00"),
        is_available=True,
    )


@pytest.fixture
def unavailable_service(db):
    """Create an unavailable service."""
    return Service.objects.create(
        name="Spa Deluxe",
        category="spa",
        description="A spa service",
        price=Decimal("200.00"),
        is_available=False,
    )


@pytest.fixture
def pet(db, client_user):
    """Create a pet owned by the client user."""
    return Pet.objects.create(
        owner=client_user,
        name="Buddy",
        species="dog",
        gender="male",
        date_of_birth=date(2020, 1, 1),
        weight=Decimal("10.00"),
    )


@pytest.fixture
def other_pet(db, other_user):
    """Create a pet owned by a different user."""
    return Pet.objects.create(
        owner=other_user,
        name="Rex",
        species="dog",
        gender="male",
        date_of_birth=date(2019, 6, 15),
        weight=Decimal("15.00"),
    )


@pytest.fixture
def cart(db, client_user):
    """Create a cart for the client user."""
    return Cart.objects.create(client=client_user)


@pytest.fixture
def validator():
    """Return a CartValidator instance."""
    return CartValidator()


# ---------------------------------------------------------------------------
# Tests: Cart non-empty rule
# ---------------------------------------------------------------------------


class TestCartNotEmpty:
    """Tests for cart_not_empty validation rule."""

    @pytest.mark.django_db
    def test_empty_cart_returns_error(self, cart, validator):
        """An empty cart should fail validation with cart_not_empty rule."""
        errors = validator.validate_for_checkout(cart)
        assert len(errors) == 1
        assert errors[0]["rule"] == "cart_not_empty"
        assert errors[0]["item_id"] is None

    @pytest.mark.django_db
    def test_cart_with_one_item_passes(self, cart, service, pet, validator):
        """A cart with one valid item should pass validation."""
        CartItem.objects.create(cart=cart, service=service, pet=pet, quantity=1)
        errors = validator.validate_for_checkout(cart)
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Cart max items rule
# ---------------------------------------------------------------------------


class TestCartMaxItems:
    """Tests for cart_max_items validation rule (>50 items)."""

    @pytest.mark.django_db
    def test_cart_with_51_items_returns_error(self, cart, client_user, validator):
        """A cart with more than 50 items should fail with cart_max_items."""
        # Create 51 different services and pets
        pet = Pet.objects.create(
            owner=client_user,
            name="Buddy",
            species="dog",
            gender="male",
            date_of_birth=date(2020, 1, 1),
            weight=Decimal("5.00"),
        )
        services = []
        for i in range(51):
            svc = Service.objects.create(
                name=f"Service {i}",
                category="grooming",
                description=f"Service {i}",
                price=Decimal("50.00"),
                is_available=True,
            )
            services.append(svc)

        for i, svc in enumerate(services):
            CartItem.objects.create(
                cart=cart,
                service=svc,
                pet=pet,
                quantity=1,
                start_date=date.today() + timedelta(days=i + 1),
                end_date=date.today() + timedelta(days=i + 2),
            )

        errors = validator.validate_for_checkout(cart)
        rule_names = [e["rule"] for e in errors]
        assert "cart_max_items" in rule_names


# ---------------------------------------------------------------------------
# Tests: Service availability rule
# ---------------------------------------------------------------------------


class TestServiceAvailability:
    """Tests for service_available validation rule."""

    @pytest.mark.django_db
    def test_unavailable_service_returns_error(
        self, cart, unavailable_service, pet, validator
    ):
        """An item with an unavailable service should fail validation."""
        CartItem.objects.create(
            cart=cart, service=unavailable_service, pet=pet, quantity=1
        )
        errors = validator.validate_for_checkout(cart)
        assert len(errors) == 1
        assert errors[0]["rule"] == "service_available"
        assert errors[0]["item_id"] is not None

    @pytest.mark.django_db
    def test_available_service_passes(self, cart, service, pet, validator):
        """An item with an available service should pass validation."""
        CartItem.objects.create(cart=cart, service=service, pet=pet, quantity=1)
        errors = validator.validate_for_checkout(cart)
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Pet ownership rule
# ---------------------------------------------------------------------------


class TestPetOwnership:
    """Tests for pet_ownership validation rule."""

    @pytest.mark.django_db
    def test_pet_not_owned_by_client_returns_error(
        self, cart, service, other_pet, validator
    ):
        """An item with a pet not owned by the cart's client should fail."""
        CartItem.objects.create(
            cart=cart, service=service, pet=other_pet, quantity=1
        )
        errors = validator.validate_for_checkout(cart)
        assert len(errors) == 1
        assert errors[0]["rule"] == "pet_ownership"

    @pytest.mark.django_db
    def test_pet_owned_by_client_passes(self, cart, service, pet, validator):
        """An item with a pet owned by the cart's client should pass."""
        CartItem.objects.create(cart=cart, service=service, pet=pet, quantity=1)
        errors = validator.validate_for_checkout(cart)
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Date range validation
# ---------------------------------------------------------------------------


class TestDateRangeValidation:
    """Tests for date range validation rules."""

    @pytest.mark.django_db
    def test_start_date_in_past_returns_error(self, cart, service, pet, validator):
        """start_date < today (UTC) should fail with date_start_not_past."""
        from datetime import datetime, timezone

        utc_today = datetime.now(timezone.utc).date()
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=utc_today - timedelta(days=1),
            end_date=utc_today + timedelta(days=5),
        )
        errors = validator.validate_for_checkout(cart)
        assert any(e["rule"] == "date_start_not_past" for e in errors)

    @pytest.mark.django_db
    def test_end_date_not_after_start_returns_error(
        self, cart, service, pet, validator
    ):
        """end_date <= start_date should fail with date_end_after_start."""
        from datetime import datetime, timezone

        utc_today = datetime.now(timezone.utc).date()
        tomorrow = utc_today + timedelta(days=1)
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=tomorrow,
            end_date=tomorrow,  # end == start
        )
        errors = validator.validate_for_checkout(cart)
        assert any(e["rule"] == "date_end_after_start" for e in errors)

    @pytest.mark.django_db
    def test_date_span_exceeds_365_days_returns_error(
        self, cart, service, pet, validator
    ):
        """A date range > 365 days should fail with date_span_max."""
        from datetime import datetime, timezone

        utc_today = datetime.now(timezone.utc).date()
        start = utc_today + timedelta(days=1)
        end = start + timedelta(days=366)
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=start,
            end_date=end,
        )
        errors = validator.validate_for_checkout(cart)
        assert any(e["rule"] == "date_span_max" for e in errors)

    @pytest.mark.django_db
    def test_valid_date_range_passes(self, cart, service, pet, validator):
        """A valid date range should pass all date validation."""
        from datetime import datetime, timezone

        utc_today = datetime.now(timezone.utc).date()
        start = utc_today
        end = start + timedelta(days=10)
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=start,
            end_date=end,
        )
        errors = validator.validate_for_checkout(cart)
        assert errors == []

    @pytest.mark.django_db
    def test_items_without_dates_pass_unconditionally(
        self, cart, service, pet, validator
    ):
        """Items with no start/end dates should pass date validation."""
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=None,
            end_date=None,
        )
        errors = validator.validate_for_checkout(cart)
        assert errors == []

    @pytest.mark.django_db
    def test_date_span_exactly_365_passes(self, cart, service, pet, validator):
        """A date range of exactly 365 days should pass."""
        from datetime import datetime, timezone

        utc_today = datetime.now(timezone.utc).date()
        start = utc_today
        end = start + timedelta(days=365)
        CartItem.objects.create(
            cart=cart,
            service=service,
            pet=pet,
            quantity=1,
            start_date=start,
            end_date=end,
        )
        errors = validator.validate_for_checkout(cart)
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: No short-circuiting (collects all errors)
# ---------------------------------------------------------------------------


class TestNoShortCircuit:
    """Tests that the validator collects ALL errors without short-circuiting."""

    @pytest.mark.django_db
    def test_multiple_errors_collected(
        self, cart, unavailable_service, other_pet, validator
    ):
        """
        An item with both unavailable service AND wrong pet ownership
        should return both errors.
        """
        CartItem.objects.create(
            cart=cart,
            service=unavailable_service,
            pet=other_pet,
            quantity=1,
        )
        errors = validator.validate_for_checkout(cart)
        rules = [e["rule"] for e in errors]
        assert "service_available" in rules
        assert "pet_ownership" in rules

    @pytest.mark.django_db
    def test_errors_across_multiple_items_collected(
        self, cart, service, unavailable_service, pet, other_pet, validator
    ):
        """All errors across multiple items should be collected."""
        # Item 1: unavailable service
        CartItem.objects.create(
            cart=cart, service=unavailable_service, pet=pet, quantity=1
        )
        # Item 2: wrong pet
        CartItem.objects.create(
            cart=cart, service=service, pet=other_pet, quantity=1
        )
        errors = validator.validate_for_checkout(cart)
        rules = [e["rule"] for e in errors]
        assert "service_available" in rules
        assert "pet_ownership" in rules
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# Tests: Error structure
# ---------------------------------------------------------------------------


class TestErrorStructure:
    """Tests that errors have the expected structure."""

    @pytest.mark.django_db
    def test_error_contains_item_id_rule_message(
        self, cart, unavailable_service, pet, validator
    ):
        """Each error dict should have item_id, rule, and message keys."""
        item = CartItem.objects.create(
            cart=cart, service=unavailable_service, pet=pet, quantity=1
        )
        errors = validator.validate_for_checkout(cart)
        assert len(errors) == 1
        error = errors[0]
        assert "item_id" in error
        assert "rule" in error
        assert "message" in error
        assert error["item_id"] == item.id
        assert isinstance(error["message"], str)
        assert len(error["message"]) > 0
