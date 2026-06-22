"""
Cart validation logic for checkout.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

from datetime import date, timezone, datetime
from typing import Any

from apps.cart.models import Cart


class CartValidator:
    """
    Validates a Cart for checkout readiness.

    Runs ALL validation rules on every CartItem, collecting all errors
    without short-circuiting. Returns a list of structured error dicts.
    An empty list indicates a valid cart.
    """

    def validate_for_checkout(self, cart: Cart) -> list[dict[str, Any]]:
        """
        Run all validation rules on cart.

        Returns a list of error dicts:
            [{"item_id": int, "rule": str, "message": str}, ...]

        An empty list means the cart is valid for checkout.
        """
        errors: list[dict[str, Any]] = []
        items = list(cart.items.select_related("service", "pet").all())

        # Rule: Cart must have at least 1 item
        if len(items) == 0:
            errors.append({
                "item_id": None,
                "rule": "cart_not_empty",
                "message": "Cart must contain at least one item.",
            })
            return errors

        # Rule: Cart must have no more than 50 items
        if len(items) > 50:
            errors.append({
                "item_id": None,
                "rule": "cart_max_items",
                "message": "Cart must contain no more than 50 items.",
            })

        today = datetime.now(timezone.utc).date()

        for item in items:
            # Rule: Service must exist and be available
            if not item.service.is_available:
                errors.append({
                    "item_id": item.id,
                    "rule": "service_available",
                    "message": (
                        f"Service '{item.service.name}' is not available."
                    ),
                })

            # Rule: Pet must belong to the authenticated client
            if item.pet.owner_id != cart.client_id:
                errors.append({
                    "item_id": item.id,
                    "rule": "pet_ownership",
                    "message": (
                        f"Pet '{item.pet.name}' does not belong to the "
                        f"authenticated client."
                    ),
                })

            # Rule: Date range validation (only if dates are present)
            if item.start_date is not None and item.end_date is not None:
                # start_date must be >= today (UTC)
                if item.start_date < today:
                    errors.append({
                        "item_id": item.id,
                        "rule": "date_start_not_past",
                        "message": (
                            "Start date must be today or in the future."
                        ),
                    })

                # end_date must be > start_date
                if item.end_date <= item.start_date:
                    errors.append({
                        "item_id": item.id,
                        "rule": "date_end_after_start",
                        "message": (
                            "End date must be after start date."
                        ),
                    })

                # Date span must not exceed 365 days
                span = (item.end_date - item.start_date).days
                if span > 365:
                    errors.append({
                        "item_id": item.id,
                        "rule": "date_span_max",
                        "message": (
                            "Date range must not exceed 365 days."
                        ),
                    })

        return errors
