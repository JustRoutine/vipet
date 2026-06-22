"""
Tests for order confirmation email logic.

Requirements: 8.4
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.emails import send_order_confirmation


@pytest.fixture
def mock_order():
    """Create a mock Order instance with related items."""
    client = MagicMock()
    client.email = "client@example.com"
    client.get_full_name.return_value = "Fatima Zahra"

    item1 = MagicMock()
    item1.service_name = "Toilettage Premium"
    item1.pet_name = "Rex"
    item1.quantity = 1
    item1.final_price = Decimal("150.00")

    item2 = MagicMock()
    item2.service_name = "Pension Luxe"
    item2.pet_name = "Milo"
    item2.quantity = 3
    item2.final_price = Decimal("900.00")

    order = MagicMock()
    order.order_number = "VIP-20250101-001"
    order.client = client
    order.total_paid = Decimal("1050.00")
    order.items.all.return_value = [item1, item2]

    return order


class TestSendOrderConfirmation:
    """Tests for send_order_confirmation function."""

    @patch("apps.orders.emails.send_mail")
    def test_sends_email_successfully(self, mock_send_mail, mock_order):
        """Email is sent with correct subject, body, and recipient."""
        result = send_order_confirmation(mock_order)

        assert result is True
        mock_send_mail.assert_called_once()

        call_kwargs = mock_send_mail.call_args[1]
        assert "VIP-20250101-001" in call_kwargs["subject"]
        assert call_kwargs["recipient_list"] == ["client@example.com"]
        assert "VIP-20250101-001" in call_kwargs["message"]
        assert "1050.00 MAD" in call_kwargs["message"]
        assert "Toilettage Premium" in call_kwargs["message"]
        assert "Pension Luxe" in call_kwargs["message"]
        assert "Rex" in call_kwargs["message"]
        assert "Milo" in call_kwargs["message"]

    @patch("apps.orders.emails.send_mail")
    def test_email_contains_html_body(self, mock_send_mail, mock_order):
        """Email includes an HTML message with service details."""
        send_order_confirmation(mock_order)

        call_kwargs = mock_send_mail.call_args[1]
        html = call_kwargs["html_message"]
        assert "VIP-20250101-001" in html
        assert "Toilettage Premium" in html
        assert "1050.00 MAD" in html

    @patch("apps.orders.emails.send_mail")
    def test_email_body_includes_all_items(self, mock_send_mail, mock_order):
        """Email body lists all order items with quantities."""
        send_order_confirmation(mock_order)

        call_kwargs = mock_send_mail.call_args[1]
        body = call_kwargs["message"]
        assert "(x1)" in body
        assert "(x3)" in body
        assert "150.00 MAD" in body
        assert "900.00 MAD" in body

    @patch("apps.orders.emails.send_mail", side_effect=Exception("SMTP error"))
    def test_handles_send_failure_gracefully(self, mock_send_mail, mock_order):
        """Returns False and logs error when send_mail raises."""
        result = send_order_confirmation(mock_order)

        assert result is False

    @patch("apps.orders.emails.send_mail")
    def test_uses_default_from_email(self, mock_send_mail, mock_order):
        """Uses DEFAULT_FROM_EMAIL setting as from_email."""
        with patch("apps.orders.emails.settings") as mock_settings:
            mock_settings.DEFAULT_FROM_EMAIL = "info@vipet.ma"
            send_order_confirmation(mock_order)

        call_kwargs = mock_send_mail.call_args[1]
        assert call_kwargs["from_email"] == "info@vipet.ma"

    @patch("apps.orders.emails.send_mail")
    def test_empty_items_list(self, mock_send_mail):
        """Works correctly when order has no items."""
        client = MagicMock()
        client.email = "test@example.com"
        client.get_full_name.return_value = "Test User"

        order = MagicMock()
        order.order_number = "VIP-00000000-000"
        order.client = client
        order.total_paid = Decimal("0.00")
        order.items.all.return_value = []

        result = send_order_confirmation(order)

        assert result is True
        mock_send_mail.assert_called_once()
