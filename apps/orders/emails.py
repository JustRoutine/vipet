"""
Order confirmation email logic for the VIPET orders app.

Requirements: 8.4
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_order_confirmation(order) -> bool:
    """
    Send an order confirmation email to the client.

    Builds an email with the order number, list of services purchased
    (service_name, pet_name, quantity, final_price for each item),
    and total amount paid. Sends to the client's email address.

    Handles email sending failures gracefully by logging the error
    without raising an exception.

    Args:
        order: An Order model instance with related items prefetched
               (order.items.all() should be available without extra queries).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    try:
        subject = f"VIPET - Confirmation de commande #{order.order_number}"

        # Build the services list
        items = order.items.all()
        lines = []
        for item in items:
            line = (
                f"  - {item.service_name} pour {item.pet_name} "
                f"(x{item.quantity}) : {item.final_price} MAD"
            )
            lines.append(line)

        services_list = "\n".join(lines)

        # Build plain text body
        body = (
            f"Bonjour {order.client.get_full_name()},\n\n"
            f"Merci pour votre commande chez VIPET !\n\n"
            f"Numéro de commande : {order.order_number}\n\n"
            f"Services commandés :\n"
            f"{services_list}\n\n"
            f"Total payé : {order.total_paid} MAD\n\n"
            f"Nous vous remercions pour votre confiance.\n"
            f"L'équipe VIPET"
        )

        # Build HTML body
        items_html = ""
        for item in items:
            items_html += (
                f"<tr>"
                f"<td>{item.service_name}</td>"
                f"<td>{item.pet_name}</td>"
                f"<td>{item.quantity}</td>"
                f"<td>{item.final_price} MAD</td>"
                f"</tr>"
            )

        html_body = (
            f"<h2>Confirmation de commande</h2>"
            f"<p>Bonjour {order.client.get_full_name()},</p>"
            f"<p>Merci pour votre commande chez VIPET !</p>"
            f"<p><strong>Numéro de commande :</strong> {order.order_number}</p>"
            f"<h3>Services commandés</h3>"
            f"<table border='1' cellpadding='5' cellspacing='0'>"
            f"<tr><th>Service</th><th>Animal</th><th>Quantité</th><th>Prix</th></tr>"
            f"{items_html}"
            f"</table>"
            f"<p><strong>Total payé : {order.total_paid} MAD</strong></p>"
            f"<p>Nous vous remercions pour votre confiance.<br>L'équipe VIPET</p>"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@vipet.ma")

        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[order.client.email],
            html_message=html_body,
            fail_silently=False,
        )

        logger.info(
            "Order confirmation email sent for order %s to %s",
            order.order_number,
            order.client.email,
        )
        return True

    except Exception as exc:
        logger.error(
            "Failed to send order confirmation email for order %s: %s",
            order.order_number,
            exc,
        )
        return False
