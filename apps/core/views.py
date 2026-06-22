"""
Custom error handler views and public page views for VIPET.

Error handlers are registered in vipet/urls.py as handler403, handler404, handler500.
Each renders a minimal branded template from templates/errors/.

Public pages:
  - HomePageView: displays 3–6 featured services (is_available=True)
  - AboutPageView: static content about VIPet

Requirements: 16.1, 16.7, 18.1, 18.2, 18.7
"""

from django.shortcuts import render
from django.views.generic import TemplateView

from apps.pets.models import Pet
from apps.services.models import Service


class HomePageView(TemplateView):
    """
    Public home page displaying featured available services and live stats.

    Context:
        featured_services: Up to 6 Service objects where is_available=True.
        stats_pets: Total number of registered pets.
        stats_categories: Number of distinct service categories available.
        stats_services: Total number of available services.

    Requirements: 18.1, 18.7
    """

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_services"] = Service.objects.filter(is_available=True)[:6]
        context["stats_pets"] = Pet.objects.count()
        context["stats_categories"] = (
            Service.objects.filter(is_available=True)
            .values("category")
            .distinct()
            .count()
        )
        context["stats_services"] = Service.objects.filter(is_available=True).count()
        return context


class AboutPageView(TemplateView):
    """
    Public about page with static content describing VIPet's mission.

    Requirements: 18.2, 18.7
    """

    template_name = "core/about.html"


def handler403(request, exception=None):
    """Render the 403 Forbidden error page."""
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None):
    """Render the 404 Not Found error page."""
    return render(request, "errors/404.html", status=404)


def handler500(request):
    """Render the 500 Internal Server Error page."""
    return render(request, "errors/500.html", status=500)
