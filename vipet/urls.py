"""
Root URL configuration for the VIPET project.

URL structure:
  /accounts/          → accounts app (register, login, logout, password-reset, profile)
  /client/            → client dashboard (pets, reservations, notifications)
  /admin-panel/       → admin dashboard (users, pets, services, reservations, gallery, contact)
  /services/          → public services listing
  /gallery/           → public gallery
  /contact/           → public contact form
  /api/v1/token/      → JWT obtain pair
  /api/v1/token/refresh/ → JWT refresh
  /api/v1/token/verify/  → JWT verify
  /api/v1/notifications/ → notifications REST API
  /api/v1/services/      → services REST API
  /api/v1/reservations/  → reservations REST API

Error handlers: 403, 404, 500 → apps.core.views

Media files are served in development via django.conf.urls.static.static().

Requirements: 16.1, 16.7
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from apps.contact.urls import admin_urlpatterns as contact_admin_urlpatterns
from apps.core import views as core_views
from apps.dashboard.urls import admin_urlpatterns as dashboard_admin_urlpatterns
from apps.dashboard.urls import client_urlpatterns as dashboard_client_urlpatterns
from apps.gallery.urls import admin_urlpatterns as gallery_admin_urlpatterns
from apps.reservations.urls import admin_urlpatterns as reservation_admin_urlpatterns
from apps.pets.api_views import PetViewSet
from apps.reservations.api_views import ReservationViewSet
from apps.services.api_views import ServiceViewSet

# ---------------------------------------------------------------------------
# DRF Router — API viewsets
# ---------------------------------------------------------------------------
router = DefaultRouter()
router.register(r"pets", PetViewSet, basename="pet")
router.register(r"reservations", ReservationViewSet, basename="reservation")
router.register(r"services", ServiceViewSet, basename="service")

# ---------------------------------------------------------------------------
# Error handlers (Requirements 16.1, 16.7)
# ---------------------------------------------------------------------------
handler403 = core_views.handler403
handler404 = core_views.handler404
handler500 = core_views.handler500

# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------
urlpatterns = [
    # Django admin site
    path("admin/", admin.site.urls),

    # -----------------------------------------------------------------------
    # Accounts (register, login, logout, password-reset, profile)
    # -----------------------------------------------------------------------
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),

    # -----------------------------------------------------------------------
    # Client dashboard  (pets, reservations, notifications)
    # -----------------------------------------------------------------------
    path("client/", include(
        (dashboard_client_urlpatterns, "dashboard"), namespace="client_dashboard"
    )),
    path("client/pets/", include("apps.pets.urls", namespace="pets")),
    path("client/reservations/", include("apps.reservations.urls", namespace="reservations")),

    # -----------------------------------------------------------------------
    # Admin dashboard (users, pets, services, reservations, gallery, contact)
    # -----------------------------------------------------------------------
    path("admin-panel/", include(
        (dashboard_admin_urlpatterns, "dashboard"), namespace="admin_dashboard"
    )),
    path("admin-panel/contact/", include(
        (contact_admin_urlpatterns, "admin_contact"), namespace="admin_contact"
    )),
    path("admin-panel/reservations/", include(
        (reservation_admin_urlpatterns, "reservations"), namespace="admin_reservations"
    )),
    path("admin-panel/gallery/", include(
        (gallery_admin_urlpatterns, "gallery"), namespace="admin_gallery"
    )),

    # -----------------------------------------------------------------------
    # Public pages routed through individual apps
    # -----------------------------------------------------------------------
    path("services/", include("apps.services.urls", namespace="services")),
    path("gallery/",  include("apps.gallery.urls",  namespace="gallery")),
    path("contact/",  include("apps.contact.urls",  namespace="contact")),

    # -----------------------------------------------------------------------
    # REST API — JWT authentication endpoints (Requirements 16.3, 16.6)
    # -----------------------------------------------------------------------
    path("api/v1/token/",         TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(),   name="token_refresh"),
    path("api/v1/token/verify/",  TokenVerifyView.as_view(),    name="token_verify"),

    # -----------------------------------------------------------------------
    # REST API — Pets, Services, Reservations (Requirements 7.2, 9.5, 12.1, 12.2)
    # -----------------------------------------------------------------------
    path("api/v1/", include(router.urls)),

    # -----------------------------------------------------------------------
    # REST API — Promotions (admin management)
    # -----------------------------------------------------------------------
    path("api/v1/promotions/", include("apps.promotions.urls", namespace="api_promotions")),

    # -----------------------------------------------------------------------
    # REST API — Orders (client order history)
    # -----------------------------------------------------------------------
    path("api/v1/orders/", include("apps.orders.urls", namespace="api_orders")),

    # -----------------------------------------------------------------------
    # REST API — Cart (client shopping cart)
    # -----------------------------------------------------------------------
    path("api/v1/cart/", include("apps.cart.urls", namespace="api_cart")),

    # -----------------------------------------------------------------------
    # REST API — Notifications
    # -----------------------------------------------------------------------
    path("api/v1/notifications/", include("apps.notifications.urls", namespace="api_notifications")),

    # -----------------------------------------------------------------------
    # Core public pages (home, about) — MUST be last to avoid catching other routes
    # -----------------------------------------------------------------------
    path("", include("apps.core.urls", namespace="core")),
]

# ---------------------------------------------------------------------------
# Serve uploaded media files in development (Requirement 17.1)
# Never serve via Django in production — use a real file server or Cloudinary.
# ---------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
