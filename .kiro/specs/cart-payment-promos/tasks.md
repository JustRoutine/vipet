# Implementation Plan: Cart, Payment & Promotions

## Overview

This plan implements the Cart, Payment & Promotions system for VIPET as three new Django apps (`cart`, `orders`, `promotions`) with a deterministic Pricing Engine, Stripe payment integration, and admin-managed promotional offers. Tasks are ordered to establish data models and pure logic first, then wire up API endpoints and integrations.

## Tasks

- [x] 1. Create promotions app with models and configuration
  - [x] 1.1 Create `apps/promotions` app with `Promotion`, `DynamicPricingRule`, `DynamicPricingTier`, and `LoyaltyTier` models
    - Create app directory structure with `__init__.py`, `apps.py`, `models.py`, `admin.py`
    - Define all four models with fields, constraints, indexes, and Meta options as specified in the design
    - Register the app in Django settings `INSTALLED_APPS`
    - Generate and apply migrations
    - _Requirements: 4.1, 4.2, 4.5, 5.1, 5.2, 5.3, 6.1, 6.2, 6.6_

  - [x] 1.2 Create promotions serializers and admin API views
    - Create `serializers.py` with `PromotionSerializer` (CRUD validation for name, dates, discount_type, discount_value), `DynamicPricingRuleSerializer` (nested tiers with contiguity validation), `LoyaltyTierSerializer` (ascending thresholds validation)
    - Create `api_views.py` with `PromotionViewSet` (admin CRUD, filterable by status/type/category), `DynamicPricingViewSet` (GET/PUT), `LoyaltyTierViewSet` (GET/PUT)
    - Create `urls.py` and register in project URL configuration
    - _Requirements: 5.1, 5.2, 5.7, 5.10, 4.5, 4.6, 6.6, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 1.3 Write property test for dynamic pricing tier contiguity validation
    - **Property 5: Dynamic pricing tier contiguity validation**
    - **Validates: Requirements 4.5, 4.6**

  - [ ]* 1.4 Write property test for promotion validation rules
    - **Property 17: Promotion validation**
    - **Validates: Requirements 5.2, 5.10, 9.3**

  - [ ]* 1.5 Write property test for promotion deletion guard
    - **Property 18: Promotion deletion guard**
    - **Validates: Requirements 9.4, 9.5**

- [x] 2. Create cart app with models and Pricing Engine
  - [x] 2.1 Create `apps/cart` app with `Cart` and `CartItem` models
    - Create app directory structure with `__init__.py`, `apps.py`, `models.py`, `admin.py`
    - Define `Cart` model with OneToOneField to client user and `CartItem` model with all fields, unique constraint, and indexes
    - Register the app in Django settings `INSTALLED_APPS`
    - Generate and apply migrations
    - _Requirements: 1.1, 1.2, 1.3, 1.11_

  - [x] 2.2 Implement the Pricing Engine in `apps/cart/pricing.py`
    - Define `PriceBreakdown` and `CartTotal` dataclasses
    - Implement `PricingEngine.calculate_item_price()` applying discounts in order: dynamic → loyalty → promotional, with half-up rounding at each step and final price clamped to ≥ 0.00
    - Implement `PricingEngine.calculate_cart_total()` summing all item breakdowns
    - Implement helper methods: `_apply_dynamic_pricing()`, `_get_loyalty_tier()`, `_select_best_promotion()`, `_apply_promotion_discount()`
    - _Requirements: 4.1, 4.2, 4.3, 5.6, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.4_

  - [ ]* 2.3 Write property test for dynamic pricing formula
    - **Property 4: Dynamic pricing formula correctness**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]* 2.4 Write property test for loyalty tier selection
    - **Property 6: Loyalty tier selection**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.7**

  - [ ]* 2.5 Write property test for discount application order
    - **Property 7: Discount application order**
    - **Validates: Requirements 7.1, 6.4**

  - [ ]* 2.6 Write property test for non-negative price clamping
    - **Property 8: Non-negative price clamping**
    - **Validates: Requirements 7.2**

  - [ ]* 2.7 Write property test for cart total consistency
    - **Property 9: Cart total consistency**
    - **Validates: Requirements 7.4**

  - [ ]* 2.8 Write property test for best promotion selection
    - **Property 10: Best promotion selection**
    - **Validates: Requirements 5.6, 5.8, 5.9**

  - [ ]* 2.9 Write property test for promotion eligibility
    - **Property 11: Promotion eligibility**
    - **Validates: Requirements 5.3**

  - [ ]* 2.10 Write property test for promotion targeting
    - **Property 12: Promotion targeting**
    - **Validates: Requirements 5.4, 5.5**

- [x] 3. Implement cart API and validation logic
  - [x] 3.1 Implement Cart serializers in `apps/cart/serializers.py`
    - Create `CartItemSerializer` with computed pricing breakdown fields (read-only), service/pet/date/quantity write fields
    - Create `CartSerializer` with nested items and computed totals (subtotal, total_discount, total_to_pay)
    - Create `AddCartItemSerializer` for item creation with deduplication logic (increment quantity if same combination exists)
    - _Requirements: 1.1, 1.2, 1.5, 1.6, 1.9, 1.10_

  - [x] 3.2 Implement Cart API views in `apps/cart/api_views.py`
    - Create `CartViewSet` with actions: retrieve (GET cart with pricing), clear (DELETE cart), add_item (POST), update_item (PATCH quantity), remove_item (DELETE item)
    - Enforce max 30 items limit on add
    - Handle unavailable service flagging in cart response
    - Create `urls.py` and register in project URL configuration
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 1.10, 1.11_

  - [x] 3.3 Implement CartValidator in `apps/cart/validators.py`
    - Implement `validate_for_checkout()` that collects all validation errors without short-circuiting
    - Validate: cart non-empty (≤50 items), services available, pets owned by client, date ranges valid (start ≥ today, end > start, span ≤ 365 days), quantity in range
    - Return structured errors identifying CartItem ID and failed rule
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 3.4 Write property test for cart item deduplication
    - **Property 1: Cart item deduplication**
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 3.5 Write property test for quantity validation range
    - **Property 2: Quantity validation range**
    - **Validates: Requirements 1.5, 1.6**

  - [ ]* 3.6 Write property test for cart total excludes unavailable services
    - **Property 3: Cart total excludes unavailable services**
    - **Validates: Requirements 1.7**

  - [ ]* 3.7 Write property test for cart validation completeness
    - **Property 13: Cart validation completeness**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.7**

  - [ ]* 3.8 Write property test for date range validation
    - **Property 14: Date range validation**
    - **Validates: Requirements 2.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create orders app with models and payment integration
  - [x] 5.1 Create `apps/orders` app with `Order` and `OrderItem` models
    - Create app directory structure with `__init__.py`, `apps.py`, `models.py`, `admin.py`
    - Define `Order` model with all fields (order_number, client, subtotal, total_discount, total_paid, stripe_payment_intent_id, status, created_at) and constraints
    - Define `OrderItem` model with full discount breakdown fields as specified in design
    - Register the app in Django settings `INSTALLED_APPS`
    - Generate and apply migrations
    - _Requirements: 3.3, 8.1_

  - [x] 5.2 Implement PaymentManager in `apps/orders/payment.py`
    - Implement `create_payment_intent()` converting MAD to centimes, using idempotency keys
    - Implement `handle_payment_success()` creating Order + OrderItems from cart, creating Reservations for date-based items, clearing the cart — all in a database transaction with `select_for_update` on PaymentIntent ID to prevent duplicates
    - Implement `generate_order_number()` for unique order numbering
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 10.5_

  - [x] 5.3 Implement Checkout view in `apps/cart/api_views.py`
    - Add `CheckoutView` that: validates cart via `CartValidator`, calculates pricing via `PricingEngine`, creates PaymentIntent via `PaymentManager`, returns `client_secret` for Stripe Elements
    - Handle payment retries (max 3 per session)
    - _Requirements: 2.1, 3.1, 3.2, 3.4, 3.5, 10.5_

  - [x] 5.4 Implement Stripe webhook handler in `apps/orders/webhooks.py`
    - Create webhook endpoint verifying Stripe signature
    - Handle `payment_intent.succeeded` event idempotently
    - Log invalid signature attempts with timestamp and source IP
    - Return appropriate HTTP responses (200 on success, 400 on invalid signature)
    - _Requirements: 3.6, 10.4_

  - [x] 5.5 Implement order confirmation email in `apps/orders/emails.py`
    - Send confirmation email with order number, services list, and total paid
    - _Requirements: 8.4_

  - [x] 5.6 Implement Order serializers and API views
    - Create `OrderSerializer` and `OrderItemSerializer` (read-only) in `apps/orders/serializers.py`
    - Create `OrderViewSet` in `apps/orders/api_views.py` with list (paginated, 20/page, sorted by `-created_at`) and retrieve actions, filtered to authenticated client only
    - Create `urls.py` and register in project URL configuration
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [ ]* 5.7 Write property test for MAD to centimes conversion
    - **Property 20: MAD to centimes conversion**
    - **Validates: Requirements 3.1**

  - [ ]* 5.8 Write property test for webhook idempotency
    - **Property 15: Webhook idempotency**
    - **Validates: Requirements 3.6**

  - [ ]* 5.9 Write property test for order preserves cart item data
    - **Property 16: Order preserves cart item data**
    - **Validates: Requirements 3.3, 3.7**

  - [ ]* 5.10 Write property test for order ownership isolation
    - **Property 19: Order ownership isolation**
    - **Validates: Requirements 8.2**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Integration wiring and security hardening
  - [x] 7.1 Wire all URL configurations and verify endpoint routing
    - Register `cart`, `orders`, and `promotions` URL patterns in the project root `urls.py` under `/api/v1/`
    - Verify all endpoints are accessible with correct authentication (client vs admin)
    - Apply `IsAuthenticated` and custom permission classes (client-only for cart/orders, admin-only for promotions management)
    - _Requirements: 1.3, 8.2, 9.1, 10.1, 10.2, 10.3_

  - [x] 7.2 Add Stripe configuration and security settings
    - Add Stripe secret key and webhook signing secret to environment variable configuration (`.env.example` update)
    - Ensure no card data fields exist in any model or serializer
    - Verify Stripe Elements integration instructions in checkout response
    - Add payment timeout handling (30s) and error response formatting
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 10.7_

  - [ ]* 7.3 Write integration tests for full checkout flow
    - Test end-to-end: add items to cart → checkout → mock Stripe PaymentIntent → webhook → order created → cart cleared → reservation created
    - Test payment failure and retry flow
    - Test concurrent webhook delivery (idempotency)
    - _Requirements: 3.1, 3.3, 3.6, 3.7, 3.8_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The Pricing Engine (task 2.2) is implemented as pure functions for easy testing without database dependencies
- Stripe interactions should be mocked in tests using `unittest.mock`
- Hypothesis (already installed) is used for all property-based tests with `@settings(max_examples=100)`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "2.2"] },
    { "id": 2, "tasks": ["1.3", "1.4", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "3.1"] },
    { "id": 3, "tasks": ["1.5", "3.2", "3.3"] },
    { "id": 4, "tasks": ["3.4", "3.5", "3.6", "3.7", "3.8", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.6"] },
    { "id": 6, "tasks": ["5.3", "5.4", "5.5"] },
    { "id": 7, "tasks": ["5.7", "5.8", "5.9", "5.10"] },
    { "id": 8, "tasks": ["7.1", "7.2"] },
    { "id": 9, "tasks": ["7.3"] }
  ]
}
```
