# Implementation Plan: VIPet Premium Services

## Overview

This plan implements the Premium Services feature as a single Django app (`apps/premium`) following established project patterns: DRF ViewSets with JWT auth, service-layer business logic, `BigAutoField` PKs, Celery background tasks, and Hypothesis property-based tests. The implementation builds incrementally from data models through services, API views, and integration, ensuring each step compiles and is testable before moving on.

## Tasks

- [ ] 1. Set up premium app structure and core configuration
  - [ ] 1.1 Create the `apps/premium` app skeleton with package directories
    - Create `apps/premium/__init__.py`, `apps/premium/apps.py` (PremiumConfig with `default_auto_field = "django.db.models.BigAutoField"`)
    - Create empty package directories: `models/`, `serializers/`, `api_views/`, `services/`, `tests/`, each with `__init__.py`
    - Create placeholder files: `tasks.py`, `permissions.py`, `validators.py`, `urls.py`, `admin.py`
    - Register the app in `INSTALLED_APPS` in `vipet/settings.py`
    - Wire `apps/premium/urls.py` into `vipet/urls.py` at `api/v1/premium/`
    - _Requirements: 14.6, 14.7_

  - [ ] 1.2 Create test infrastructure with fixtures and factories
    - Create `apps/premium/tests/conftest.py` with shared pytest fixtures: `client_user`, `admin_user`, `other_client`, `pet`, `reservation` (status="approved"), `api_client` (authenticated JWT)
    - Create `apps/premium/tests/factories.py` with factory_boy factories for all premium models (VanFactory, TransportBookingFactory, GPSLocationFactory, EventThemeFactory, EventTierFactory, EventAddOnFactory, EventBookingFactory, CameraFactory, StreamAccessFactory, MediaUpdateFactory)
    - _Requirements: 1.1–14.8_

- [ ] 2. Implement Transport domain models and service
  - [ ] 2.1 Create Transport models (Van, TransportBooking, GPSLocation)
    - Implement `apps/premium/models/transport.py` with Van, TransportBooking, GPSLocation models exactly as specified in the design
    - Include ALLOWED_TRANSITIONS, `can_transition_to()`, `transition_to()` methods on TransportBooking
    - Include all Meta classes with indexes and ordering
    - Export models from `apps/premium/models/__init__.py`
    - Run `makemigrations` and `migrate`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 3.1, 3.4, 4.1, 4.5_

  - [ ] 2.2 Implement TransportService with booking, status, and van logic
    - Implement `apps/premium/services/transport.py` with `TransportService` class
    - `create_booking()`: validate reservation.status=="approved", pet ownership, future datetime within reservation range, non-empty address ≤500 chars; create booking with status "scheduled"; send Notification
    - `advance_status()`: validate allowed transition, save, send Notification
    - `cancel_booking()`: validate cancellable states (scheduled, en_route_pickup for client; admin can cancel from same states), transition to cancelled, send Notification
    - `assign_van()`: validate van is_active=True, no conflicting active bookings on same van, assign van + driver_name
    - `get_current_location()`: return most recent GPSLocation by recorded_at
    - `get_route_history()`: return all GPSLocations ordered by recorded_at ascending
    - _Requirements: 1.1–1.9, 2.1–2.7, 3.2, 3.3, 4.2, 4.3, 4.4, 13.1_

  - [ ]* 2.3 Write property test for Transport Status State Machine
    - **Property 2: Transport Status State Machine**
    - Test that for any (current_status, target_status) pair, transition succeeds iff target is in ALLOWED_TRANSITIONS[current_status]
    - **Validates: Requirements 2.1, 2.2, 2.6, 2.7**

  - [ ]* 2.4 Write property test for Reservation Approved Gate (Transport)
    - **Property 1: Reservation Approved Gate**
    - Test that transport booking creation succeeds only when reservation.status == "approved"
    - **Validates: Requirements 1.5, 5.5, 8.2, 10.2**

  - [ ]* 2.5 Write property test for Transport Datetime Validation
    - **Property 6: Transport Datetime Validation**
    - Test that booking is accepted only if datetime is strictly in the future AND within reservation [start_date, end_date]
    - **Validates: Requirements 1.3, 1.7**

  - [ ]* 2.6 Write property test for Pickup Address Validation
    - **Property 7: Pickup Address Validation**
    - Test that booking is accepted only if address is non-empty after trim AND ≤500 characters
    - **Validates: Requirements 1.6**

  - [ ]* 2.7 Write property test for Van Uniqueness Constraints
    - **Property 11: Van Uniqueness Constraints**
    - Test that duplicate registration_plate or gps_device_id rejects with error identifying duplicate field
    - **Validates: Requirements 4.5**

  - [ ]* 2.8 Write property test for Van Assignment Conflict Detection
    - **Property 12: Van Assignment Conflict Detection**
    - Test that van assignment succeeds only if van is_active=True AND no conflicting active booking
    - **Validates: Requirements 4.3**

- [ ] 3. Implement Transport API views and serializers
  - [ ] 3.1 Create Transport serializers
    - Implement `apps/premium/serializers/transport.py` with VanSerializer, TransportBookingListSerializer, TransportBookingDetailSerializer, TransportBookingCreateSerializer, GPSLocationSerializer
    - CreateSerializer validates direction choices, pickup_address, scheduled_at; uses service layer for creation
    - _Requirements: 1.1, 1.6, 1.7, 4.1_

  - [ ] 3.2 Create Transport API views
    - Implement `apps/premium/api_views/transport.py` with TransportBookingViewSet and VanViewSet
    - TransportBookingViewSet: list (IsClient, filtered by client), retrieve (IsClient+IsOwner), create (IsClient), cancel action (IsClient+IsOwner), advance action (IsAdmin), assign_van action (IsAdmin), location action (IsClient+IsOwner), route action (IsClient+IsOwner)
    - VanViewSet: list (IsAdmin), create (IsAdmin), partial_update (IsAdmin), deactivate action (IsAdmin)
    - Wire endpoints into `apps/premium/urls.py`
    - _Requirements: 1.1–1.9, 2.1–2.7, 3.2, 3.3, 3.5, 4.1–4.5, 14.1, 14.6_

  - [ ]* 3.3 Write unit tests for Transport API endpoints
    - Test booking creation with valid data returns 201
    - Test booking creation with past datetime returns 400
    - Test cancellation from eligible/ineligible states
    - Test admin advance status transitions
    - Test 403 for accessing another client's booking
    - Test 401 for unauthenticated access
    - Test van CRUD and deactivation
    - _Requirements: 1.1–1.9, 2.1–2.7, 4.1–4.5, 14.1, 14.7, 14.8_

- [ ] 4. Checkpoint - Ensure Transport domain tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Event domain models and service
  - [ ] 5.1 Create Event models (EventTheme, EventTier, EventAddOn, EventBooking)
    - Implement `apps/premium/models/events.py` with all four models as specified in the design
    - Include ALLOWED_TRANSITIONS, `can_transition_to()`, `transition_to()` on EventBooking
    - Include UniqueConstraint for unique_pet_event_per_day
    - Export from `apps/premium/models/__init__.py`
    - Run `makemigrations` and `migrate`
    - _Requirements: 5.1–5.9, 6.1–6.5, 7.1_

  - [ ] 5.2 Implement EventService with booking, pricing, and lifecycle logic
    - Implement `apps/premium/services/events.py` with `EventService` class
    - `create_booking()`: validate reservation approved, event date within reservation range, event time 08:00–20:00, theme available, no duplicate pet event on same date; calculate total price; create booking; send Notification
    - `calculate_total_price()`: tier.base_price + sum(add_on.price), rounded to 2 decimal places
    - `confirm_booking()`: pending → confirmed, Notification
    - `complete_booking()`: confirmed → completed, Notification
    - `cancel_booking()`: role-based cancellation (client: pending only; staff: pending/confirmed)
    - _Requirements: 5.1–5.9, 7.1–7.6, 13.2_

  - [ ]* 5.3 Write property test for Event Status State Machine
    - **Property 3: Event Status State Machine**
    - Test that for any (role, current_status, target_status) triple, transition succeeds iff valid per ALLOWED_TRANSITIONS AND user has required role
    - **Validates: Requirements 7.1, 7.5, 7.6**

  - [ ]* 5.4 Write property test for Event Price Calculation
    - **Property 13: Event Price Calculation**
    - Test that total_price == tier.base_price + sum(add_on prices), rounded to 2 decimal places
    - **Validates: Requirements 5.7**

  - [ ]* 5.5 Write property test for Event Date Within Reservation Range
    - **Property 14: Event Date Within Reservation Range**
    - Test that event booking is accepted only if start_date ≤ event_date ≤ end_date
    - **Validates: Requirements 5.2**

  - [ ]* 5.6 Write property test for Event Time Within Operating Hours
    - **Property 15: Event Time Within Operating Hours**
    - Test that event booking is accepted only if 08:00 ≤ event_time ≤ 20:00
    - **Validates: Requirements 5.3**

  - [ ]* 5.7 Write property test for No Duplicate Events Per Pet Per Date
    - **Property 16: No Duplicate Events Per Pet Per Date**
    - Test that at most one event booking with status in (pending, confirmed) exists per (pet, date)
    - **Validates: Requirements 5.4**

- [ ] 6. Implement Event API views and serializers
  - [ ] 6.1 Create Event serializers
    - Implement `apps/premium/serializers/events.py` with EventThemeSerializer, EventTierSerializer, EventAddOnSerializer, EventBookingListSerializer, EventBookingDetailSerializer, EventBookingCreateSerializer
    - CreateSerializer validates theme availability, event date/time, add-on references
    - _Requirements: 5.1–5.9, 6.1–6.5_

  - [ ] 6.2 Create Event API views
    - Implement `apps/premium/api_views/events.py` with EventBookingViewSet, EventThemeViewSet, EventTierViewSet, EventAddOnViewSet
    - EventBookingViewSet: list (IsClient), retrieve (IsClient+IsOwner), create (IsClient), cancel (IsClient+IsOwner), confirm (IsAdmin), complete (IsAdmin)
    - Theme/Tier/AddOn ViewSets: list (Authenticated), create/update (IsAdmin)
    - Wire into `apps/premium/urls.py`
    - _Requirements: 5.1–5.9, 6.1–6.5, 7.1–7.6, 14.2, 14.6_

  - [ ]* 6.3 Write unit tests for Event API endpoints
    - Test event booking creation with valid data
    - Test price calculation correctness
    - Test status transitions (confirm, complete, cancel)
    - Test duplicate pet event constraint
    - Test theme/tier/add-on CRUD by admin
    - Test unavailable theme exclusion from client list
    - Test 403 for wrong client access
    - _Requirements: 5.1–5.9, 6.1–6.5, 7.1–7.6, 14.2_

  - [ ]* 6.4 Write property test for Unavailable Themes Excluded
    - **Property 17: Unavailable Themes Excluded from Client List**
    - Test that client-facing list only contains themes with is_available=True
    - **Validates: Requirements 6.5**

- [ ] 7. Checkpoint - Ensure Event domain tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement Streaming domain models and service
  - [ ] 8.1 Create Streaming models (Camera, StreamAccess)
    - Implement `apps/premium/models/streaming.py` with Camera and StreamAccess models as specified
    - Include UniqueConstraint for camera location
    - Export from `apps/premium/models/__init__.py`
    - Run `makemigrations` and `migrate`
    - _Requirements: 8.1–8.8, 9.1–9.5_

  - [ ] 8.2 Implement StreamService with access generation and revocation
    - Implement `apps/premium/services/streaming.py` with `StreamService` class
    - `generate_access()`: validate reservation approved, camera active, camera location matches reservation location, revoke previous active access for same (reservation, camera), generate cryptographic token (secrets.token_urlsafe(96)), set expires_at = now + 2h, build HLS URL, create StreamAccess record
    - `revoke_camera_accesses()`: set is_active=False for all active accesses on a camera, return count
    - _Requirements: 8.1–8.8, 9.3, 9.4_

  - [ ]* 8.3 Write property test for Stream Token Uniqueness and Expiration
    - **Property 18: Stream Token Uniqueness and Expiration**
    - Test that access_token is unique and expires_at == created_at + 2 hours
    - **Validates: Requirements 8.1**

  - [ ]* 8.4 Write property test for Camera-Location Matching
    - **Property 19: Camera-Location Matching**
    - Test that access is granted only when camera location matches reservation location
    - **Validates: Requirements 8.3**

  - [ ]* 8.5 Write property test for At Most One Active Stream Per (Reservation, Camera)
    - **Property 20: At Most One Active Stream Per (Reservation, Camera)**
    - Test that after generation, exactly one StreamAccess with is_active=True exists for the pair
    - **Validates: Requirements 8.5**

- [ ] 9. Implement Streaming API views and serializers
  - [ ] 9.1 Create Streaming serializers
    - Implement `apps/premium/serializers/streaming.py` with CameraSerializer, StreamAccessSerializer, StreamAccessCreateSerializer
    - CreateSerializer validates camera_id and reservation_id, delegates to service
    - _Requirements: 8.1–8.8, 9.1–9.5_

  - [ ] 9.2 Create Streaming API views
    - Implement `apps/premium/api_views/streaming.py` with StreamAccessViewSet and CameraViewSet
    - StreamAccessViewSet: create (IsClient), list active accesses (IsClient, filtered by client)
    - CameraViewSet: list (IsAdmin), create (IsAdmin), partial_update (IsAdmin), deactivate action (IsAdmin) — deactivate revokes all active accesses
    - Wire into `apps/premium/urls.py`
    - _Requirements: 8.1–8.8, 9.1–9.5, 14.5, 14.6_

  - [ ]* 9.3 Write unit tests for Streaming API endpoints
    - Test stream access generation with valid inputs
    - Test revocation of previous access on regeneration
    - Test camera deactivation revokes all accesses
    - Test 403 for wrong client
    - Test camera-location mismatch rejection
    - _Requirements: 8.1–8.8, 9.1–9.5, 14.5_

- [ ] 10. Implement Media domain models and service
  - [ ] 10.1 Create Media model (MediaUpdate)
    - Implement `apps/premium/models/media.py` with MediaUpdate model as specified
    - Export from `apps/premium/models/__init__.py`
    - Run `makemigrations` and `migrate`
    - _Requirements: 10.1–10.9, 11.1–11.5_

  - [ ] 10.2 Implement MediaService with upload and validation
    - Implement `apps/premium/services/media.py` with `MediaService` class
    - `upload_media()`: validate staff role, reservation approved, pet linked to reservation, validate file; create MediaUpdate record; queue `generate_thumbnail` task; send Notification to reservation client
    - `validate_file()`: check format (photo: JPEG/PNG/WEBP ≤10MB; video: MP4 ≤100MB ≤60s duration); return list of error messages
    - _Requirements: 10.1–10.9, 13.3_

  - [ ]* 10.3 Write unit tests for Media upload and gallery
    - Test successful photo upload creates MediaUpdate + queues thumbnail task
    - Test invalid format returns 400 with specific error
    - Test file too large returns 400
    - Test video duration exceeded returns 400
    - Test media list returns paginated results sorted by created_at desc
    - Test empty gallery returns empty list
    - Test 403 for wrong client viewing media
    - _Requirements: 10.1–10.9, 11.1–11.5, 14.3, 14.4_

- [ ] 11. Implement Media API views and serializers
  - [ ] 11.1 Create Media serializers
    - Implement `apps/premium/serializers/media.py` with MediaUpdateListSerializer (thumbnail, type, caption, timestamp), MediaUpdateDetailSerializer (full URL, size, duration), MediaUploadSerializer (file, media_type, reservation, pet, caption)
    - _Requirements: 10.1, 11.1, 11.3, 11.4_

  - [ ] 11.2 Create Media API views
    - Implement `apps/premium/api_views/media.py` with MediaUpdateViewSet
    - create action (IsAdmin — staff upload), list action (IsClient+IsOwner, filtered by reservation query param, paginated 20/page), retrieve action (IsClient+IsOwner)
    - Wire into `apps/premium/urls.py`
    - _Requirements: 10.1–10.9, 11.1–11.5, 14.3, 14.4, 14.6_

- [ ] 12. Checkpoint - Ensure Streaming and Media domain tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement GPS, Thumbnail, and Token Expiry Celery tasks
  - [ ] 13.1 Implement Celery background tasks
    - Implement `apps/premium/tasks.py` with three Celery tasks:
    - `poll_gps_location(transport_booking_id)`: fetch GPS from device API, store GPSLocation record, re-schedule self if booking still in active transit status; handle API unreachable gracefully (log + skip)
    - `generate_thumbnail(media_update_id)`: generate thumbnail from photo/video file, save to thumbnail field; retry up to 3 times with exponential backoff
    - `check_stream_expiry()`: periodic task (every 5 min), find StreamAccess expiring within 10 min, create Notification for each client
    - _Requirements: 2.3, 2.4, 3.1, 3.6, 3.7, 10.7, 13.4_

  - [ ]* 13.2 Write property test for GPS Coordinate Validation
    - **Property 8: GPS Coordinate Validation**
    - Test that latitude is within [-90, 90], longitude within [-180, 180], and recorded_at not in the future
    - **Validates: Requirements 3.4**

  - [ ]* 13.3 Write property test for GPS Current Location Returns Most Recent
    - **Property 9: GPS Current Location Returns Most Recent**
    - Test that current location query returns the record with maximum recorded_at
    - **Validates: Requirements 3.2**

  - [ ]* 13.4 Write property test for GPS Route History Ordering
    - **Property 10: GPS Route History Ordering**
    - Test that route history returns records ordered by recorded_at ascending
    - **Validates: Requirements 3.3**

- [ ] 14. Implement permissions, validators, and shared utilities
  - [ ] 14.1 Create premium-specific permissions and validators
    - Implement `apps/premium/permissions.py` with `IsPremiumOwner` permission class (checks client ownership on premium resources using reservation.client field)
    - Implement `apps/premium/validators.py` with shared validation utilities: `validate_reservation_approved()`, `validate_pet_ownership()`, `validate_future_datetime_in_range()`
    - _Requirements: 14.1–14.8_

  - [ ]* 14.2 Write property test for Ownership Access Control
    - **Property 4: Ownership Access Control**
    - Test that client accessing another client's resource gets 403 without revealing resource existence
    - **Validates: Requirements 1.8, 3.5, 8.7, 11.2, 14.1, 14.2, 14.4, 14.5, 14.8**

  - [ ]* 14.3 Write property test for Pet-Reservation Linkage
    - **Property 5: Pet-Reservation Linkage**
    - Test that operation succeeds only when pet belongs to client AND is linked to specified reservation
    - **Validates: Requirements 1.4, 10.3**

- [ ] 15. Wire premium URL configuration and admin registration
  - [ ] 15.1 Finalize URL routing for all premium endpoints
    - Complete `apps/premium/urls.py` with all transport, event, streaming, and media routes under `/api/v1/premium/`
    - Verify all 40+ endpoints are correctly wired with proper HTTP method mappings
    - _Requirements: 1.1–14.8_

  - [ ] 15.2 Register premium models in Django admin
    - Implement `apps/premium/admin.py` with ModelAdmin classes for Van, TransportBooking, EventTheme, EventTier, EventAddOn, EventBooking, Camera, StreamAccess, MediaUpdate
    - Include list_display, list_filter, search_fields for each
    - _Requirements: 4.1, 6.1, 6.2, 6.4, 9.1_

- [ ] 16. Implement Cart integration for premium services
  - [ ] 16.1 Add ContentType fields to CartItem and wire premium bookings
    - Add `content_type` (FK to ContentType, null=True) and `object_id` (PositiveIntegerField, null=True) fields to CartItem model
    - Add `GenericForeignKey('content_type', 'object_id')` for polymorphic reference
    - Create migration for CartItem changes
    - Update pricing engine to apply loyalty + promo discounts to premium items (no dynamic pricing for non-boarding)
    - _Requirements: 12.1–12.5_

  - [ ]* 16.2 Write integration tests for Cart + premium services
    - Test adding TransportBooking to cart creates CartItem with correct price
    - Test adding EventBooking to cart with total_price
    - Test cancelled premium booking flagged as unavailable in cart
    - Test checkout with premium items updates booking status
    - _Requirements: 12.1–12.5_

- [ ] 17. Implement integration tests for background tasks and notifications
  - [ ]* 17.1 Write integration tests for Celery tasks and notification flow
    - Test GPS polling task stores location records (mock GPS API)
    - Test thumbnail generation task (mock file processor)
    - Test stream expiry check creates notifications for expiring tokens
    - Test notification creation within 5 seconds of status change
    - Test cart integration end-to-end flow
    - _Requirements: 2.3, 2.4, 3.1, 3.6, 10.7, 12.1–12.5, 13.1–13.5_

- [ ] 18. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at domain boundaries
- Property tests validate the 20 universal correctness properties defined in the design using Hypothesis
- Unit tests validate specific examples, edge cases, and API contract behavior
- The project already uses Hypothesis (`.hypothesis/` directory exists) and pytest with `@pytest.mark.django_db`
- All services use the existing `Notification.objects.create(user=client, message=...)` pattern
- State machine patterns follow the same `ALLOWED_TRANSITIONS` + `transition_to()` approach as `apps/reservations`
- Permission classes extend the existing `IsClient`, `IsAdmin`, `IsOwner` from `apps/core/permissions`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "5.1", "8.1", "10.1", "14.1"] },
    { "id": 3, "tasks": ["2.2", "5.2", "8.2", "10.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "5.3", "5.4", "5.5", "5.6", "5.7", "8.3", "8.4", "8.5", "14.2", "14.3"] },
    { "id": 5, "tasks": ["3.1", "6.1", "9.1", "11.1"] },
    { "id": 6, "tasks": ["3.2", "6.2", "9.2", "11.2", "13.1"] },
    { "id": 7, "tasks": ["3.3", "6.3", "6.4", "9.3", "10.3", "13.2", "13.3", "13.4"] },
    { "id": 8, "tasks": ["15.1", "15.2"] },
    { "id": 9, "tasks": ["16.1"] },
    { "id": 10, "tasks": ["16.2", "17.1"] }
  ]
}
```
