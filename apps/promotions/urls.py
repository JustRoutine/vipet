"""
URL configuration for the promotions app API.

Routes:
  /api/v1/promotions/                  → PromotionViewSet (list, create)
  /api/v1/promotions/{id}/             → PromotionViewSet (retrieve, update, destroy)
  /api/v1/promotions/dynamic-pricing/  → DynamicPricingViewSet (GET, PUT)
  /api/v1/promotions/loyalty-tiers/    → LoyaltyTierViewSet (GET, PUT)

Requirements: 5.1, 5.2, 5.7, 5.10, 4.5, 4.6, 6.6, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.promotions.api_views import (
    DynamicPricingViewSet,
    LoyaltyTierViewSet,
    PromotionViewSet,
)

router = DefaultRouter()
router.register(r"", PromotionViewSet, basename="promotion")

app_name = "api_promotions"

urlpatterns = [
    # Dynamic pricing and loyalty tiers must come before the router
    # to avoid being captured by the viewset's {pk} pattern
    path("dynamic-pricing/", DynamicPricingViewSet.as_view(), name="dynamic-pricing"),
    path("loyalty-tiers/", LoyaltyTierViewSet.as_view(), name="loyalty-tiers"),
    path("", include(router.urls)),
]
