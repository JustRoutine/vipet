"""
Stripe webhook handler for the orders app.

Verifies Stripe webhook signatures, handles payment_intent.succeeded events
idempotently, and logs invalid signature attempts.

Requirements: 3.6, 10.4
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.orders.payment import PaymentManager

logger = logging.getLogger(__name__)


def _get_client_ip(request: HttpRequest) -> str:
    """Extract the client IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """
    Stripe webhook endpoint.

    Verifies the Stripe signature, handles payment_intent.succeeded events
    idempotently, and returns appropriate HTTP responses.

    - 200 on successful processing or acknowledged-but-ignored event types
    - 400 on invalid signature
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    # Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        # Invalid payload
        logger.warning(
            "Stripe webhook invalid payload: timestamp=%s, source_ip=%s, reason=invalid_payload",
            datetime.now(timezone.utc).isoformat(),
            _get_client_ip(request),
        )
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.warning(
            "Stripe webhook signature verification failed: timestamp=%s, source_ip=%s, reason=%s",
            datetime.now(timezone.utc).isoformat(),
            _get_client_ip(request),
            str(e),
        )
        return HttpResponse(status=400)

    # Handle event types
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent["id"]

        try:
            payment_manager = PaymentManager()
            order = payment_manager.handle_payment_success(payment_intent_id)

            # Send order confirmation email (handles failures gracefully)
            from apps.orders.emails import send_order_confirmation

            send_order_confirmation(order)

        except Exception:
            logger.exception(
                "Error handling payment_intent.succeeded for PaymentIntent %s",
                payment_intent_id,
            )
            return HttpResponse(status=500)

    # For all other event types, acknowledge but ignore
    return HttpResponse(status=200)
