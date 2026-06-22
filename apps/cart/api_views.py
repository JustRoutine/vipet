"""
Cart API views for the VIPET REST API.

Provides endpoints for managing the client's shopping cart:
  - GET /api/v1/cart/           → Retrieve cart with all items and pricing
  - POST /api/v1/cart/items/    → Add item to cart
  - PATCH /api/v1/cart/items/{id}/ → Update item quantity
  - DELETE /api/v1/cart/items/{id}/ → Remove item from cart
  - DELETE /api/v1/cart/        → Clear entire cart
  - POST /api/v1/cart/checkout/ → Validate cart and create PaymentIntent

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 1.10, 1.11, 2.1, 3.1, 3.2, 3.4, 3.5, 10.5
"""

import logging
import uuid

import stripe
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart, CartItem
from apps.cart.serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
)
from apps.cart.validators import CartValidator
from apps.core.permissions import IsClient
from apps.orders.payment import PaymentManager

logger = logging.getLogger(__name__)


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for client cart operations.

    Requires JWT authentication + client role.
    Each client has a single server-side cart that persists across sessions.

    Actions:
      - list (GET /cart/)             → Retrieve cart with pricing breakdown
      - clear (DELETE /cart/)          → Clear all items from cart
      - add_item (POST /cart/items/)  → Add a new item to cart
      - update_item (PATCH /cart/items/{pk}/) → Update item quantity
      - remove_item (DELETE /cart/items/{pk}/) → Remove an item
    """

    permission_classes = [permissions.IsAuthenticated, IsClient]

    def _get_or_create_cart(self, user):
        """Get or create the client's cart."""
        cart, _ = Cart.objects.get_or_create(client=user)
        return cart

    # ------------------------------------------------------------------
    # GET /api/v1/cart/ → Retrieve the client's cart with pricing
    # ------------------------------------------------------------------
    def list(self, request):
        """
        Retrieve the client's cart with all items and computed pricing.

        Returns the full cart with item-level pricing breakdowns and
        cart totals (subtotal, total_discount, total_to_pay).
        Unavailable services are flagged and excluded from totals.

        Requirements: 1.7, 1.9, 1.10
        """
        cart = self._get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={"request": request, "client": request.user})
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # DELETE /api/v1/cart/ → Clear the entire cart
    # ------------------------------------------------------------------
    def clear(self, request):
        """
        Clear all items from the client's cart.

        Requirements: 1.4
        """
        cart = self._get_or_create_cart(request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # POST /api/v1/cart/items/ → Add item to cart
    # ------------------------------------------------------------------
    def add_item(self, request):
        """
        Add an item to the client's cart.

        Deduplication: if the same (service, pet, start_date, end_date)
        combination already exists, increments the quantity.

        Enforces a maximum of 30 cart items.

        Requirements: 1.1, 1.2, 1.11
        """
        cart = self._get_or_create_cart(request.user)

        # Enforce max 30 items limit (Requirement 1.11)
        current_item_count = cart.items.count()
        if current_item_count >= 30:
            # Check if this would be a deduplication (increment existing)
            # Allow increment of existing item even at 30 items
            service_id = request.data.get("service")
            pet_id = request.data.get("pet")
            start_date = request.data.get("start_date")
            end_date = request.data.get("end_date")

            existing = CartItem.objects.filter(
                cart=cart,
                service_id=service_id,
                pet_id=pet_id,
                start_date=start_date,
                end_date=end_date,
            ).exists()

            if not existing:
                return Response(
                    {"detail": "Le panier ne peut pas contenir plus de 30 articles."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = AddCartItemSerializer(
            data=request.data,
            context={"request": request, "cart": cart},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        # Return the created/updated item with pricing breakdown
        item_serializer = CartItemSerializer(
            item,
            context={"request": request, "client": request.user},
        )
        return Response(item_serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # PATCH /api/v1/cart/items/{pk}/ → Update item quantity
    # ------------------------------------------------------------------
    def update_item(self, request, item_pk=None):
        """
        Update the quantity of a cart item.

        Accepts a JSON body with {"quantity": <int>} where quantity
        must be between 1 and 50 inclusive.

        Requirements: 1.5, 1.6
        """
        cart = self._get_or_create_cart(request.user)

        try:
            item = cart.items.get(pk=item_pk)
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Article non trouvé dans le panier."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate quantity
        quantity = request.data.get("quantity")
        if quantity is None:
            return Response(
                {"detail": "Le champ 'quantity' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"detail": "La quantité doit être un nombre entier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1 or quantity > 50:
            return Response(
                {"detail": "La quantité doit être comprise entre 1 et 50."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save()

        item_serializer = CartItemSerializer(
            item,
            context={"request": request, "client": request.user},
        )
        return Response(item_serializer.data)

    # ------------------------------------------------------------------
    # DELETE /api/v1/cart/items/{pk}/ → Remove item from cart
    # ------------------------------------------------------------------
    def remove_item(self, request, item_pk=None):
        """
        Remove a single item from the client's cart.

        Requirements: 1.4
        """
        cart = self._get_or_create_cart(request.user)

        try:
            item = cart.items.get(pk=item_pk)
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Article non trouvé dans le panier."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Maximum number of payment retry attempts per checkout session
MAX_PAYMENT_RETRIES = 3


class CheckoutView(APIView):
    """
    Initiate checkout: validate cart, create Stripe PaymentIntent.

    POST /api/v1/cart/checkout/

    Validates the client's cart using CartValidator, generates an
    idempotency key, creates a PaymentIntent via PaymentManager,
    and returns the client_secret for Stripe Elements on the frontend.

    Handles payment retries (max 3 per session) and Stripe errors.

    Requirements: 2.1, 3.1, 3.2, 3.4, 3.5, 10.5
    """

    permission_classes = [permissions.IsAuthenticated, IsClient]

    def post(self, request):
        """
        Process checkout request.

        Returns:
            200: {"client_secret": "...", "payment_intent_id": "..."}
            400: {"errors": [...]} if cart validation fails
            402: {"detail": "..."} if payment creation fails
            503: {"detail": "..."} if network timeout
        """
        # Check retry count from session (Requirement 3.4)
        retry_count = request.session.get("checkout_retry_count", 0)
        if retry_count >= MAX_PAYMENT_RETRIES:
            return Response(
                {
                    "detail": (
                        "Nombre maximum de tentatives de paiement atteint. "
                        "Veuillez réessayer plus tard."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Get the client's cart
        try:
            cart = Cart.objects.get(client=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"errors": [{"item_id": None, "rule": "cart_not_empty", "message": "Cart must contain at least one item."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate cart via CartValidator (Requirement 2.1)
        validator = CartValidator()
        validation_errors = validator.validate_for_checkout(cart)

        if validation_errors:
            return Response(
                {"errors": validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate a unique idempotency key (Requirement 10.5)
        idempotency_key = str(uuid.uuid4())

        # Create PaymentIntent via PaymentManager
        payment_manager = PaymentManager()

        try:
            payment_intent = payment_manager.create_payment_intent(
                cart=cart,
                idempotency_key=idempotency_key,
            )
        except stripe.error.CardError as e:
            # Card was declined (Requirement 3.4)
            request.session["checkout_retry_count"] = retry_count + 1
            request.session.save()
            return Response(
                {"detail": e.user_message or "Votre carte a été refusée."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except stripe.error.InvalidRequestError as e:
            logger.error("Stripe InvalidRequestError during checkout: %s", str(e))
            request.session["checkout_retry_count"] = retry_count + 1
            request.session.save()
            return Response(
                {"detail": "Une erreur est survenue lors du traitement du paiement."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.AuthenticationError:
            # Invalid Stripe API key (Requirement 10.7)
            logger.error(
                "Stripe AuthenticationError: API key is invalid or missing."
            )
            return Response(
                {
                    "detail": (
                        "Le traitement des paiements est temporairement "
                        "indisponible."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except stripe.error.APIConnectionError:
            # Network timeout / connectivity issue (Requirement 3.5)
            request.session["checkout_retry_count"] = retry_count + 1
            request.session.save()
            return Response(
                {
                    "detail": (
                        "Problème de connectivité avec le service de paiement. "
                        "Veuillez réessayer."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except stripe.error.StripeError as e:
            # Generic Stripe error
            logger.error("Stripe error during checkout: %s", str(e))
            request.session["checkout_retry_count"] = retry_count + 1
            request.session.save()
            return Response(
                {"detail": "Une erreur est survenue lors du traitement du paiement."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ValueError as e:
            # Cart total out of allowed range
            logger.error("Payment amount validation error: %s", str(e))
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Success: reset retry counter and return client_secret
        request.session["checkout_retry_count"] = 0
        request.session.save()

        return Response(
            {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
            },
            status=status.HTTP_200_OK,
        )
