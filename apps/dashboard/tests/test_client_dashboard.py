"""
Unit tests for the Client Dashboard view.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import pytest
from datetime import date, timedelta
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from apps.dashboard.views import ClientDashboardView
from apps.pets.models import Pet
from apps.reservations.models import Reservation
from apps.services.models import Service

User = get_user_model()


@pytest.fixture
def client_user(db):
    """Create a client user."""
    return User.objects.create_user(
        email="client@example.com",
        password="TestPass123!",
        first_name="Jane",
        last_name="Doe",
        role="client",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        email="admin@example.com",
        password="TestPass123!",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


@pytest.fixture
def service(db):
    """Create a test service."""
    return Service.objects.create(
        name="Luxury Suite",
        category="luxury_suite",
        description="Premium suite for pets",
        price="99.99",
        is_available=True,
    )


@pytest.fixture
def pets(db, client_user):
    """Create multiple pets for the client."""
    pets_list = []
    for i in range(3):
        pet = Pet.objects.create(
            owner=client_user,
            name=f"Pet{i}",
            species="dog",
            gender="male",
            date_of_birth=date(2020, 1, 1),
            weight="10.00",
        )
        pets_list.append(pet)
    return pets_list


@pytest.fixture
def reservations(db, client_user, pets, service):
    """Create multiple reservations for the client."""
    reservations_list = []
    for i in range(7):
        reservation = Reservation.objects.create(
            client=client_user,
            pet=pets[0],
            service=service,
            start_date=date.today() + timedelta(days=i + 1),
            end_date=date.today() + timedelta(days=i + 2),
            status="pending",
        )
        reservations_list.append(reservation)
    return reservations_list


@pytest.mark.django_db
class TestClientDashboardView:
    """Tests for ClientDashboardView."""

    def test_client_can_access_dashboard(self, client, client_user):
        """Requirement 15.1: Authenticated client can access dashboard."""
        client.force_login(client_user)
        response = client.get("/client/")
        assert response.status_code == 200

    def test_unauthenticated_user_gets_403(self, client):
        """Requirement 15.3: Unauthenticated user cannot access dashboard."""
        response = client.get("/client/")
        assert response.status_code == 403

    def test_admin_user_gets_403(self, client, admin_user):
        """Requirement 15.4: Admin user gets 403 on client dashboard."""
        client.force_login(admin_user)
        response = client.get("/client/")
        assert response.status_code == 403

    def test_context_contains_pet_count(self, client, client_user, pets):
        """Requirement 15.1: Dashboard displays pet count."""
        client.force_login(client_user)
        response = client.get("/client/")
        assert response.context["pet_count"] == 3

    def test_context_contains_recent_reservations(
        self, client, client_user, reservations
    ):
        """Requirement 15.1: Dashboard displays 5 most recent reservations."""
        client.force_login(client_user)
        response = client.get("/client/")
        recent = response.context["recent_reservations"]
        assert len(recent) == 5

    def test_recent_reservations_ordered_by_created_at_desc(
        self, client, client_user, reservations
    ):
        """Requirement 15.1: Reservations ordered by creation date descending."""
        client.force_login(client_user)
        response = client.get("/client/")
        recent = list(response.context["recent_reservations"])
        created_dates = [r.created_at for r in recent]
        assert created_dates == sorted(created_dates, reverse=True)

    def test_zero_pets_shows_zero_count(self, client, client_user):
        """Requirement 15.5: Zero pets displays count of 0."""
        client.force_login(client_user)
        response = client.get("/client/")
        assert response.context["pet_count"] == 0

    def test_zero_reservations_shows_empty_list(self, client, client_user):
        """Requirement 15.5: Zero reservations displays empty list."""
        client.force_login(client_user)
        response = client.get("/client/")
        assert len(response.context["recent_reservations"]) == 0

    def test_only_own_pets_counted(self, client, client_user, db):
        """Requirement 15.1: Only client's own pets are counted."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="TestPass123!",
            first_name="Other",
            last_name="User",
            role="client",
        )
        # Create pets for both users
        Pet.objects.create(
            owner=client_user,
            name="MyPet",
            species="cat",
            gender="female",
            date_of_birth=date(2021, 5, 5),
            weight="5.00",
        )
        Pet.objects.create(
            owner=other_user,
            name="OtherPet",
            species="dog",
            gender="male",
            date_of_birth=date(2020, 3, 3),
            weight="15.00",
        )
        client.force_login(client_user)
        response = client.get("/client/")
        assert response.context["pet_count"] == 1

    def test_only_own_reservations_shown(self, client, client_user, service, db):
        """Requirement 15.1: Only client's own reservations are shown."""
        other_user = User.objects.create_user(
            email="other2@example.com",
            password="TestPass123!",
            first_name="Other",
            last_name="User2",
            role="client",
        )
        other_pet = Pet.objects.create(
            owner=other_user,
            name="OtherPet",
            species="dog",
            gender="male",
            date_of_birth=date(2020, 1, 1),
            weight="10.00",
        )
        Reservation.objects.create(
            client=other_user,
            pet=other_pet,
            service=service,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            status="pending",
        )
        client.force_login(client_user)
        response = client.get("/client/")
        assert len(response.context["recent_reservations"]) == 0
