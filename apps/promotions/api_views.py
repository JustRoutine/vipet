"""
Promotions API views for the VIPET REST API.

Provides admin-only ViewSets for managing promotions, dynamic pricing rules,
and loyalty tiers.

Endpoints:
  - PromotionViewSet: Full CRUD with filtering by status/type/category
  - DynamicPricingViewSet: GET/PUT for the active dynamic pricing rule
  - LoyaltyTierViewSet: GET/PUT for the loyalty tier configuration

Requirements: 5.1, 5.2, 5.7, 5.10, 4.5, 4.6, 6.6, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardResultsSetPagination
from apps.core.permissions import IsAdmin
from apps.promotions.models import (
    DynamicPricingRule,
    LoyaltyTier,
    Promotion,
)
from apps.promotions.serializers import (
    DynamicPricingRuleSerializer,
    LoyaltyTierListSerializer,
    LoyaltyTierSerializer,
    PromotionSerializer,
)


class PromotionViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Promotions.

    - List: paginated (20/page), sorted by start_date descending
    - Filterable by: is_active (status), discount_type (type), target_categories (category)
    - Create: validates name, dates, discount constraints
    - Update: validates discount_value > 0, end_date > start_date, percentage ≤ 50
    - Delete: only allowed if promotion has not been applied to any order

    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """

    serializer_class = PromotionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "is_active": ["exact"],
        "discount_type": ["exact"],
    }

    def get_queryset(self):
        """
        Return promotions with optional category filter.

        Query parameters:
            is_active (bool): Filter by active/inactive status
            discount_type (str): Filter by 'percentage' or 'fixed'
            target_category (str): Filter by target category (JSON array contains)
        """
        queryset = Promotion.objects.all().order_by("-start_date")

        # Additional filter: target_category (not a model field — uses JSONField contains)
        target_category = self.request.query_params.get("target_category", "").strip()
        if target_category:
            queryset = queryset.filter(target_categories__contains=target_category)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        Delete a promotion only if it has not been applied to any order.

        If the promotion is referenced by OrderItems (via promotion_name),
        reject deletion and suggest deactivation.

        Requirements: 9.4, 9.5
        """
        promotion = self.get_object()

        # Check if any OrderItem references this promotion
        # We check by promotion name since OrderItem stores promotion_name
        try:
            from apps.orders.models import OrderItem

            has_orders = OrderItem.objects.filter(
                promotion_name=promotion.name
            ).exists()
        except (ImportError, Exception):
            # Orders app not yet installed — no orders can reference this promotion
            has_orders = False

        if has_orders:
            return Response(
                {
                    "detail": (
                        "Cette promotion est liée à des commandes existantes "
                        "et ne peut pas être supprimée. "
                        "Vous pouvez la désactiver en définissant is_active sur False."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)


class DynamicPricingViewSet(APIView):
    """
    GET/PUT endpoint for dynamic pricing rule configuration.

    - GET: Returns the active dynamic pricing rule with nested tiers
    - PUT: Replaces the entire tier configuration (validates contiguity)

    Requirements: 4.5, 4.6
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        """Return the active dynamic pricing rule with tiers."""
        rule = DynamicPricingRule.objects.filter(is_active=True).first()
        if not rule:
            return Response(
                {"detail": "Aucune règle de tarification dynamique active trouvée."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DynamicPricingRuleSerializer(rule)
        return Response(serializer.data)

    def put(self, request):
        """Update the active dynamic pricing rule and its tiers."""
        rule = DynamicPricingRule.objects.filter(is_active=True).first()
        if not rule:
            return Response(
                {"detail": "Aucune règle de tarification dynamique active trouvée."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DynamicPricingRuleSerializer(rule, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LoyaltyTierViewSet(APIView):
    """
    GET/PUT endpoint for loyalty tier configuration.

    - GET: Returns all loyalty tiers sorted by min_bookings
    - PUT: Replaces the entire loyalty tier configuration (validates ascending thresholds)

    Requirements: 6.6
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        """Return all loyalty tiers sorted by min_bookings ascending."""
        tiers = LoyaltyTier.objects.all().order_by("min_bookings")
        serializer = LoyaltyTierSerializer(tiers, many=True)
        return Response({"tiers": serializer.data})

    def put(self, request):
        """Replace all loyalty tiers with the new configuration."""
        serializer = LoyaltyTierListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_tiers = serializer.update(None, serializer.validated_data)
        response_serializer = LoyaltyTierSerializer(created_tiers, many=True)
        return Response({"tiers": response_serializer.data})
