"""
Integration tests for URL routing and permission enforcement.

Verifies that:
- All cart, orders, and promotions endpoints are accessible under /api/v1/
- Cart and orders endpoints require IsAuthenticated + IsClient
- Promotions management endpoints require IsAuthenticated + IsAdmin
- Stripe webhook endpoint requires no DRF authentication (uses signature verification)

Requirements: 1.3, 8.2, 9.1, 10.1, 10.2, 10.3
"""

import pytest
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser


@pytest.fixture
def client_user(db):
    """Create a client user for testing."""
    return CustomUser.objects.create_user(
        email="client@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Client",
        role="client",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    return CustomUser.objects.create_user(
        email="admin@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Admin",
        role="admin",
        is_staff=True,
    )


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def client_api_client(api_client, client_user):
    """Return an API client authenticated as a client user."""
    api_client.force_authenticate(user=client_user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Return an API client authenticated as an admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# ============================================================================
# URL Resolution Tests
# ============================================================================

class TestCartURLResolution:
    """Verify cart endpoints resolve under /api/v1/cart/."""

    def test_cart_detail_resolves(self):
        url = reverse("api_cart:cart-detail")
        assert url == "/api/v1/cart/"

    def test_cart_add_item_resolves(self):
        url = reverse("api_cart:cart-add-item")
        assert url == "/api/v1/cart/items/"

    def test_cart_item_detail_resolves(self):
        match = resolve("/api/v1/cart/items/1/")
        assert match.url_name == "cart-item-detail"

    def test_cart_checkout_resolves(self):
        url = reverse("api_cart:cart-checkout")
        assert url == "/api/v1/cart/checkout/"


class TestOrdersURLResolution:
    """Verify orders endpoints resolve under /api/v1/orders/."""

    def test_order_list_resolves(self):
        url = reverse("api_orders:order-list")
        assert url == "/api/v1/orders/"

    def test_order_detail_resolves(self):
        match = resolve("/api/v1/orders/1/")
        assert match.url_name == "order-detail"

    def test_webhook_resolves(self):
        url = reverse("api_orders:stripe-webhook")
        assert url == "/api/v1/orders/webhook/stripe/"


class TestPromotionsURLResolution:
    """Verify promotions endpoints resolve under /api/v1/promotions/."""

    def test_promotion_list_resolves(self):
        url = reverse("api_promotions:promotion-list")
        assert url == "/api/v1/promotions/"

    def test_promotion_detail_resolves(self):
        match = resolve("/api/v1/promotions/1/")
        assert match.url_name == "promotion-detail"

    def test_dynamic_pricing_resolves(self):
        url = reverse("api_promotions:dynamic-pricing")
        assert url == "/api/v1/promotions/dynamic-pricing/"

    def test_loyalty_tiers_resolves(self):
        url = reverse("api_promotions:loyalty-tiers")
        assert url == "/api/v1/promotions/loyalty-tiers/"


# ============================================================================
# Permission Enforcement Tests — Cart (client-only)
# ============================================================================

@pytest.mark.django_db
class TestCartPermissions:
    """Cart endpoints require IsAuthenticated + IsClient."""

    def test_unauthenticated_cannot_access_cart(self, api_client):
        """Unauthenticated requests get 401."""
        response = api_client.get("/api/v1/cart/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_cannot_access_cart(self, admin_api_client):
        """Admin users get 403 on cart endpoints (client-only)."""
        response = admin_api_client.get("/api/v1/cart/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_client_can_access_cart(self, client_api_client):
        """Authenticated client can access their cart."""
        response = client_api_client.get("/api/v1/cart/")
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_checkout(self, api_client):
        """Unauthenticated requests get 401 on checkout."""
        response = api_client.post("/api/v1/cart/checkout/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_cannot_checkout(self, admin_api_client):
        """Admin users get 403 on checkout (client-only)."""
        response = admin_api_client.post("/api/v1/cart/checkout/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Permission Enforcement Tests — Orders (client-only, except webhook)
# ============================================================================

@pytest.mark.django_db
class TestOrdersPermissions:
    """Orders endpoints require IsAuthenticated + IsClient (except webhook)."""

    def test_unauthenticated_cannot_list_orders(self, api_client):
        """Unauthenticated requests get 401."""
        response = api_client.get("/api/v1/orders/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_cannot_list_orders(self, admin_api_client):
        """Admin users get 403 on orders (client-only)."""
        response = admin_api_client.get("/api/v1/orders/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_client_can_list_orders(self, client_api_client):
        """Authenticated client can access their orders."""
        response = client_api_client.get("/api/v1/orders/")
        assert response.status_code == status.HTTP_200_OK

    def test_webhook_no_auth_required(self, api_client):
        """Webhook endpoint doesn't require DRF auth (uses Stripe signature)."""
        # POST with empty body — will fail signature verification (400)
        # but should NOT return 401/403
        response = api_client.post(
            "/api/v1/orders/webhook/stripe/",
            data=b"{}",
            content_type="application/json",
        )
        # 400 means it reached the view (signature verification failed)
        # Not 401 or 403 (no auth required)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Permission Enforcement Tests — Promotions (admin-only)
# ============================================================================

@pytest.mark.django_db
class TestPromotionsPermissions:
    """Promotions management endpoints require IsAuthenticated + IsAdmin."""

    def test_unauthenticated_cannot_list_promotions(self, api_client):
        """Unauthenticated requests get 401."""
        response = api_client.get("/api/v1/promotions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_client_cannot_list_promotions(self, client_api_client):
        """Client users get 403 on promotions (admin-only)."""
        response = client_api_client.get("/api/v1/promotions/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list_promotions(self, admin_api_client):
        """Authenticated admin can access promotions."""
        response = admin_api_client.get("/api/v1/promotions/")
        assert response.status_code == status.HTTP_200_OK

    def test_client_cannot_access_dynamic_pricing(self, client_api_client):
        """Client users get 403 on dynamic pricing (admin-only)."""
        response = client_api_client.get("/api/v1/promotions/dynamic-pricing/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_client_cannot_access_loyalty_tiers(self, client_api_client):
        """Client users get 403 on loyalty tiers (admin-only)."""
        response = client_api_client.get("/api/v1/promotions/loyalty-tiers/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_dynamic_pricing(self, admin_api_client):
        """Authenticated admin can access dynamic pricing config."""
        response = admin_api_client.get("/api/v1/promotions/dynamic-pricing/")
        # 404 is acceptable if no active rule exists, but not 401/403
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_can_access_loyalty_tiers(self, admin_api_client):
        """Authenticated admin can access loyalty tiers config."""
        response = admin_api_client.get("/api/v1/promotions/loyalty-tiers/")
        assert response.status_code == status.HTTP_200_OK
