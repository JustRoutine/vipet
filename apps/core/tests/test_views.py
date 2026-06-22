"""
Tests for core public page views (HomePageView, AboutPageView).

Requirements: 18.1, 18.2, 18.7
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.services.models import Service


@pytest.mark.django_db
class TestHomePageView:
    """Tests for the public home page at /."""

    def test_home_page_returns_200(self, client: Client):
        """Home page is accessible without authentication (Req 18.7)."""
        response = client.get(reverse("core:home"))
        assert response.status_code == 200

    def test_home_page_uses_correct_template(self, client: Client):
        """Home page renders core/home.html template."""
        response = client.get(reverse("core:home"))
        assert "core/home.html" in [t.name for t in response.templates]

    def test_home_page_shows_featured_services(self, client: Client):
        """Home page shows available services in context (Req 18.1)."""
        # Create available services
        for i in range(4):
            Service.objects.create(
                name=f"Service {i}",
                category="grooming",
                description="A test service",
                price="50.00",
                is_available=True,
            )
        # Create an unavailable service
        Service.objects.create(
            name="Unavailable Service",
            category="spa",
            description="Not available",
            price="75.00",
            is_available=False,
        )

        response = client.get(reverse("core:home"))
        featured = response.context["featured_services"]

        # Should have 4 available services, not the unavailable one
        assert len(featured) == 4
        assert all(s.is_available for s in featured)

    def test_home_page_limits_to_six_services(self, client: Client):
        """Home page shows maximum 6 featured services (Req 18.1)."""
        for i in range(10):
            Service.objects.create(
                name=f"Service {i}",
                category="daycare",
                description="A service",
                price="30.00",
                is_available=True,
            )

        response = client.get(reverse("core:home"))
        featured = response.context["featured_services"]
        assert len(featured) == 6

    def test_home_page_url_resolves_to_root(self):
        """Home page is served at the root URL / (Req 18.1)."""
        assert reverse("core:home") == "/"


@pytest.mark.django_db
class TestAboutPageView:
    """Tests for the public about page at /about/."""

    def test_about_page_returns_200(self, client: Client):
        """About page is accessible without authentication (Req 18.7)."""
        response = client.get(reverse("core:about"))
        assert response.status_code == 200

    def test_about_page_uses_correct_template(self, client: Client):
        """About page renders core/about.html template."""
        response = client.get(reverse("core:about"))
        assert "core/about.html" in [t.name for t in response.templates]

    def test_about_page_url_resolves_correctly(self):
        """About page is served at /about/ (Req 18.2)."""
        assert reverse("core:about") == "/about/"
