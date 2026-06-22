"""
URL configuration for the cart app API.

Routes:
  GET    /api/v1/cart/              → Retrieve cart with pricing breakdown
  DELETE /api/v1/cart/              → Clear entire cart
  POST   /api/v1/cart/items/       → Add item to cart
  PATCH  /api/v1/cart/items/{id}/  → Update item quantity
  DELETE /api/v1/cart/items/{id}/  → Remove item from cart
  POST   /api/v1/cart/checkout/    → Validate cart and create PaymentIntent

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 1.10, 1.11, 2.1, 3.1, 3.2, 3.4, 3.5, 10.5
"""

from django.urls import path

from apps.cart.api_views import CartViewSet, CheckoutView

app_name = "api_cart"

# Manual URL wiring for the CartViewSet actions
# (Custom action-based ViewSet rather than standard ModelViewSet)
cart_list = CartViewSet.as_view({"get": "list", "delete": "clear"})
cart_add_item = CartViewSet.as_view({"post": "add_item"})
cart_item_detail = CartViewSet.as_view({"patch": "update_item", "delete": "remove_item"})

urlpatterns = [
    path("", cart_list, name="cart-detail"),
    path("items/", cart_add_item, name="cart-add-item"),
    path("items/<int:item_pk>/", cart_item_detail, name="cart-item-detail"),
    path("checkout/", CheckoutView.as_view(), name="cart-checkout"),
]
