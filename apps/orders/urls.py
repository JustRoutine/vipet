"""
URL configuration for the orders app API.

Routes:
  GET  /api/v1/orders/                → List client's orders (paginated)
  GET  /api/v1/orders/{id}/           → Order detail with items
  POST /api/v1/orders/webhook/stripe/ → Stripe webhook endpoint

Requirements: 3.6, 8.1, 8.2, 8.3, 8.5, 10.4
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.orders.api_views import OrderViewSet
from apps.orders.webhooks import stripe_webhook

app_name = "api_orders"

router = DefaultRouter()
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    path("webhook/stripe/", stripe_webhook, name="stripe-webhook"),
] + router.urls
