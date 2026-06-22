# Requirements Document

## Introduction

This document defines the requirements for the Cart, Payment & Promotions System of the VIPET luxury pet hotel platform. The system enables clients to aggregate multiple services into a shopping cart, pay securely via credit card through a payment gateway, benefit from dynamic pricing for boarding stays, and receive promotional and loyalty discounts. Administrators can create and manage promotional offers with configurable rules.

## Glossary

- **Cart**: A temporary collection of cart items belonging to a single authenticated client, representing services the client intends to purchase
- **Cart_Item**: A single line item within a Cart, linking a Service to a Pet with optional date range and quantity
- **Order**: A finalized purchase record created from a Cart after successful payment, containing the total amount paid and payment metadata
- **Order_Item**: A single line item within an Order, preserving the service, pet, price, and discount details at the time of purchase
- **Payment_Gateway**: The external payment processing service (Stripe) used to securely process credit card transactions
- **Payment_Intent**: A Stripe object representing the intent to collect a payment, tracking the payment lifecycle
- **Promotion**: A discount offer created by an administrator with a percentage or fixed amount, applicable to specific services or categories, with a validity period
- **Loyalty_Discount**: An automatic discount applied based on the client's historical usage (number of completed reservations) of a specific service or category
- **Dynamic_Pricing_Rule**: A pricing rule for boarding/hotel services where the per-day rate decreases as the number of booked days increases (volume discount tiers)
- **Pricing_Engine**: The component responsible for calculating the final price of a cart item by applying dynamic pricing rules, promotions, and loyalty discounts in the correct order
- **Client**: An authenticated user with role "client" who books services for their pets
- **Admin**: An authenticated user with role "admin" who manages the platform
- **Service**: An existing VIPET service offering (grooming, boarding, spa, training, transport, birthday_events, veterinary_checkup) with a base price in MAD

## Requirements

### Requirement 1: Cart Creation and Management

**User Story:** As a client, I want to add multiple services to a shopping cart, so that I can combine different services into a single order before checkout.

#### Acceptance Criteria

1. WHEN a client adds a service to the cart, THE Cart SHALL create a Cart_Item linking the selected Service, the selected Pet, and optional start/end dates, with an initial quantity of 1
2. WHEN a client adds a service that already exists in the cart for the same pet and same dates, THE Cart SHALL increment the quantity of the existing Cart_Item instead of creating a duplicate
3. THE Cart SHALL persist server-side for the authenticated client across browser sessions until the cart is explicitly cleared or converted to an Order
4. WHEN a client removes a Cart_Item, THE Cart SHALL delete only that item and recalculate the cart total
5. WHEN a client updates the quantity of a Cart_Item, THE Cart SHALL accept only positive integer values between 1 and 50 inclusive, and recalculate the cart total
6. IF a client attempts to set a Cart_Item quantity to a value less than 1 or greater than 50, THEN THE Cart SHALL reject the update and display an error message indicating the allowed range
7. IF a Service referenced by a Cart_Item becomes unavailable (is_available=False), THEN THE Cart SHALL flag that item as unavailable and exclude it from the cart total
8. IF a Pet referenced by a Cart_Item is deleted by the client, THEN THE Cart SHALL remove the associated Cart_Item and recalculate the cart total
9. THE Cart SHALL display each Cart_Item with the service name, pet name, dates (if applicable), unit price in MAD, quantity, applicable discount amount in MAD, and line total in MAD
10. THE Cart SHALL display the cart subtotal, total discount amount, and final total to pay, all in MAD rounded to 2 decimal places
11. THE Cart SHALL accept a maximum of 30 Cart_Items; IF a client attempts to add beyond this limit, THEN THE Cart SHALL reject the addition and display an error message indicating the maximum has been reached

### Requirement 2: Cart Validation Before Checkout

**User Story:** As a client, I want the system to validate my cart before payment, so that I only pay for valid and available services.

#### Acceptance Criteria

1. WHEN a client initiates checkout, THE Cart SHALL validate that the cart contains at least one and no more than 50 Cart_Items
2. WHEN a client initiates checkout, THE Cart SHALL validate that all referenced Services exist and have is_available=True
3. WHEN a client initiates checkout, THE Cart SHALL validate that all referenced Pets exist and belong to the authenticated client
4. WHEN a client initiates checkout, THE Cart SHALL validate that Cart_Items with date ranges have start_date >= today (server date, UTC) and end_date > start_date, and that the date range does not exceed 365 days
5. WHEN a client initiates checkout, THE Cart SHALL execute all validation rules on every Cart_Item and collect all failures before returning a response
6. IF any validation fails during checkout initiation, THEN THE Cart SHALL reject the checkout and return a list of validation errors, where each error identifies the specific Cart_Item (by ID) and the validation rule that failed
7. IF any validation fails during checkout initiation, THEN THE Cart SHALL preserve all Cart_Items in the cart without modification, allowing the client to correct or remove invalid items before retrying

### Requirement 3: Payment Processing via Stripe

**User Story:** As a client, I want to pay for my cart by credit card, so that I can securely complete my booking.

#### Acceptance Criteria

1. WHEN a client confirms checkout with a valid cart, THE Payment_Gateway SHALL create a Payment_Intent with the cart total amount in MAD (centimes), where the amount is between 100 centimes (1 MAD) and 99,999,999 centimes (999,999.99 MAD) inclusive
2. THE Payment_Gateway SHALL collect credit card details (card number, expiration date, CVC) using Stripe Elements on the client side without transmitting raw card data to the VIPET server
3. WHEN Stripe confirms payment success, THE System SHALL create an Order record with status "paid", store the Stripe Payment_Intent ID, and copy all Cart_Items into Order_Items preserving the service, pet, dates, quantity, unit price, and applied discounts at the time of payment
4. WHEN Stripe reports payment failure, THE System SHALL display an error message to the client indicating the Stripe-provided decline reason, preserve the cart contents, and allow the client to retry payment up to 3 additional attempts within the same checkout session
5. IF a network error occurs during payment processing and no response is received from Stripe within 30 seconds, THEN THE System SHALL display an error message indicating a connectivity issue, preserve the cart contents, and allow the client to retry
6. WHEN a Stripe webhook event of type "payment_intent.succeeded" is received and no corresponding Order with "paid" status exists for that Payment_Intent ID, THE System SHALL create the Order record with status "paid" and associated Reservation records, ensuring the same Payment_Intent ID is never processed into more than one Order
7. WHEN an Order is successfully created, THE System SHALL create a Reservation record with status "pending" for each Order_Item that includes date ranges
8. WHEN an Order is successfully created, THE System SHALL clear the client's cart by deleting all Cart_Items associated with that client

### Requirement 4: Dynamic Pricing for Boarding Services

**User Story:** As a client, I want to get a lower per-day rate when I book boarding for more days, so that longer stays are more affordable.

#### Acceptance Criteria

1. WHILE a Cart_Item references a Service in a boarding category (including "luxury_suite") with a date range, THE Pricing_Engine SHALL calculate the total boarding price as: (service base_rate per day) × (number of days) × (1 - applicable tier discount percentage), where number of days equals end_date minus start_date and must be between 1 and 365 inclusive
2. THE Dynamic_Pricing_Rule SHALL define discount tiers: 1-3 days at 0% discount (base rate), 4-7 days at 10% discount per day, 8-14 days at 15% discount per day, 15-365 days at 20% discount per day, where a single tier applies to the entire stay based on total number of days
3. WHEN the number of booked days changes (via date modification), THE Pricing_Engine SHALL recalculate the per-day rate according to the applicable tier and update the Cart_Item total within the same request
4. THE Cart SHALL display for each boarding Cart_Item: the original per-day rate in MAD, the discounted per-day rate in MAD (rounded to two decimal places using banker's rounding), the number of days, the discount percentage applied, and the total line price in MAD
5. THE Admin SHALL be able to modify the discount tier day-range thresholds and discount percentages (between 0% and 50% inclusive) via the admin panel without code changes
6. IF the Admin submits a Dynamic_Pricing_Rule configuration where tier day-ranges overlap or have gaps, THEN THE System SHALL reject the configuration and display an error message indicating the invalid tier boundaries

### Requirement 5: Promotional Offers Management

**User Story:** As an admin, I want to create promotional offers with discounts on services, so that I can attract more clients during specific periods.

#### Acceptance Criteria

1. THE Admin SHALL be able to create a Promotion with: name (maximum 100 characters), description (maximum 500 characters), discount type (percentage or fixed amount in MAD), discount value, start date, end date, and target (specific services or entire categories)
2. WHEN the Admin submits a new Promotion, THE System SHALL validate that: the name is not empty, the start date is before the end date, the start date is not in the past, the discount value is between 1 and 50 (inclusive) for percentage type, and the discount value is between 1.00 MAD and 10,000.00 MAD for fixed amount type
3. WHILE a Promotion has is_active=True AND start_date <= today <= end_date, THE Promotion SHALL be considered active and eligible for application by the Pricing_Engine
4. WHEN a Promotion targets a specific service, THE Pricing_Engine SHALL apply the discount to Cart_Items containing that service
5. WHEN a Promotion targets a category, THE Pricing_Engine SHALL apply the discount to all Cart_Items containing services in that category
6. IF multiple Promotions apply to the same Cart_Item, THEN THE Pricing_Engine SHALL calculate the effective discount amount of each (percentage applied to the item's base price, or fixed amount) and apply only the single promotion yielding the highest discount amount in MAD for the client
7. THE Admin SHALL be able to deactivate a Promotion before its end_date by setting an is_active flag to False, which immediately removes it from eligibility regardless of date range
8. WHEN a Promotion is a percentage discount, THE Pricing_Engine SHALL calculate the discount on the base price (before dynamic pricing adjustments) and cap the discount at 50% of the base price
9. WHEN a Promotion is a fixed amount discount, THE Pricing_Engine SHALL subtract the fixed amount from the item price and set the resulting price to 0.00 MAD if the subtraction would produce a negative value
10. IF the Admin attempts to create a Promotion with invalid fields, THEN THE System SHALL reject the creation and display an error message indicating which fields failed validation

### Requirement 6: Loyalty and Duration Discounts

**User Story:** As a frequent client, I want to receive automatic discounts based on my booking history, so that my loyalty is rewarded.

#### Acceptance Criteria

1. THE Loyalty_Discount SHALL be calculated based on the number of completed reservations (status="completed") the client has for the same service category, where clients with fewer than 5 completed bookings receive no loyalty discount
2. THE Loyalty_Discount tiers SHALL be: 5-9 completed bookings = 5% discount, 10-19 completed bookings = 8% discount, 20+ completed bookings = 12% discount
3. WHEN a client adds a Cart_Item, THE Pricing_Engine SHALL check the client's completed reservation count for that service's category and apply the appropriate Loyalty_Discount tier as a percentage of the dynamically-priced amount for that item
4. THE Loyalty_Discount SHALL be applied after dynamic pricing but before promotional discounts, and SHALL be recalculated at checkout initiation to reflect any reservations completed since the item was added to the cart
5. THE Cart SHALL display the loyalty discount for each applicable Cart_Item showing the tier name, the discount percentage, and the discount amount in MAD as a separate line from promotional discounts
6. THE Admin SHALL be able to modify the loyalty tier thresholds and percentages via the admin panel without code changes, where discount percentages must be between 1% and 50% inclusive and tier thresholds must be positive integers in ascending order
7. IF a client's completed reservation count does not meet the minimum threshold of the lowest loyalty tier, THEN THE Pricing_Engine SHALL apply no Loyalty_Discount and THE Cart SHALL not display a loyalty discount line for that Cart_Item

### Requirement 7: Discount Stacking and Calculation Order

**User Story:** As a client, I want to understand how my final price is calculated, so that I can see the value of each discount applied.

#### Acceptance Criteria

1. THE Pricing_Engine SHALL apply discounts in the following order: (1) Dynamic pricing for boarding, (2) Loyalty discount on the dynamically-priced amount, (3) Promotional discount on the loyalty-discounted amount, rounding each intermediate result to 2 decimal places (centimes) using half-up rounding
2. IF the sum of all applied discounts for a Cart_Item exceeds the pre-discount price, THEN THE Pricing_Engine SHALL clamp the final price to 0.00 MAD and reduce the last-applied discount to only the remaining amount
3. THE Cart SHALL display a price breakdown for each Cart_Item showing: base price in MAD, dynamic pricing adjustment as an amount in MAD (if applicable), loyalty discount as both percentage and amount in MAD (if applicable), promotional discount as both percentage or fixed label and amount in MAD (if applicable), and the final price in MAD
4. THE Pricing_Engine SHALL produce consistent totals such that summing individually calculated Cart_Item final prices equals the displayed cart total, with no rounding discrepancy exceeding 0.01 MAD across the entire cart

### Requirement 8: Order History and Receipts

**User Story:** As a client, I want to view my past orders and payment receipts, so that I can track my spending.

#### Acceptance Criteria

1. THE System SHALL store each Order with: order number, client reference, list of Order_Items, subtotal, total discount, final amount paid, Stripe Payment_Intent ID, payment status (one of: "paid", "refunded", "failed"), and creation timestamp
2. WHEN a client views their order history, THE System SHALL display only the Orders belonging to the authenticated client, sorted by creation date descending, paginated with a maximum of 20 Orders per page
3. THE System SHALL provide a detail view for each Order showing all Order_Items with service name, pet name, dates (if applicable), base price, dynamic pricing adjustment (if applicable), loyalty discount (if applicable), promotional discount (if applicable), and final price paid per item
4. WHEN an Order is created, THE System SHALL send a confirmation email to the client within 60 seconds containing the order number, list of services purchased, and final total amount paid
5. IF a client has no past Orders, THEN THE System SHALL display an empty state message indicating no orders have been placed

### Requirement 9: Admin Promotion Dashboard

**User Story:** As an admin, I want to view and manage all promotions from a dashboard, so that I can monitor active campaigns.

#### Acceptance Criteria

1. THE Admin panel SHALL display a paginated list of all Promotions (20 items per page) sorted by start_date descending, showing name, discount type, value, target, start/end dates, and active status
2. THE Admin SHALL be able to filter Promotions by: active/inactive status, discount type, and target category, where multiple selected filters are combined with AND logic
3. WHEN the Admin edits an existing Promotion's details (name, description, discount value, dates, target, active status), THE System SHALL validate that discount_value is greater than zero, end_date is after start_date, and percentage discount_value does not exceed 50
4. THE Admin SHALL be able to delete a Promotion that has not been applied to any Order (no Order_Item references the Promotion via promotion_applied)
5. IF a Promotion has been applied to at least one Order, THEN THE System SHALL prevent deletion, display a message indicating the Promotion is linked to existing orders, and allow only deactivation by setting is_active to False
6. IF the Admin submits an edit with invalid values, THEN THE System SHALL reject the update, preserve the existing Promotion data, and display error messages identifying each invalid field

### Requirement 10: Payment Security and PCI Compliance

**User Story:** As a client, I want my payment information to be handled securely, so that my financial data is protected.

#### Acceptance Criteria

1. THE System SHALL never store, log, or transmit raw credit card numbers, CVCs, or full expiration dates on the VIPET server
2. THE System SHALL use Stripe Elements (client-side) to tokenize card information before any server interaction
3. THE System SHALL communicate with Stripe API exclusively over HTTPS using the server-side secret key stored in environment variables
4. IF a Stripe webhook signature verification fails, THEN THE System SHALL reject the webhook payload with a 400 response status, and log the attempt including the timestamp, source IP address, and the reason for signature failure
5. THE System SHALL use idempotency keys, unique per cart checkout attempt, when creating Payment_Intents to prevent duplicate charges in case of network retries
6. IF Stripe Elements fails to load or initialize on the client side, THEN THE System SHALL display an error message indicating that the payment form is unavailable and SHALL prevent the client from submitting payment data
7. IF the Stripe API secret key is missing or invalid when processing a payment request, THEN THE System SHALL reject the checkout attempt, display an error message indicating that payment processing is temporarily unavailable, and SHALL NOT expose the key configuration details to the client
