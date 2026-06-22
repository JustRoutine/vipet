# Implementation Plan: VIPET Full Platform

## Overview

This plan implements the remaining VIPET platform modules: Pet management, Reservations with state machine, Notifications with signal-driven creation, Gallery, Contact, Dashboard (admin/client), Services views/API, and Public pages. Each task builds incrementally on the previous, wiring components together progressively. Existing code (CustomUser, Service model, accounts app, core validators, JWT endpoints, base settings) is leveraged throughout.

## Tasks

- [x] 1. Implement data models and migrations
  - [x] 1.1 Implement Pet model
    - Create `apps/pets/models.py` with the Pet model as specified in design (species, gender, vaccination choices; owner FK to AUTH_USER_MODEL; weight decimal; photo with upload_to; indexes)
    - Add `clean()` method for weight validation (0.01–999.99) and date_of_birth not in future
    - Generate and apply migration
    - _Requirements: 7.1, 7.7, 7.8, 7.9_

  - [x] 1.2 Implement Reservation model
    - Create `apps/reservations/models.py` with the Reservation model as specified in design (STATUS_CHOICES, ALLOWED_TRANSITIONS dict, client/pet/service FKs, date fields, status with db_index, indexes)
    - Implement `can_transition_to()` and `transition_to()` methods
    - Add `clean()` method for date validation (start_date >= today, end_date > start_date)
    - Generate and apply migration
    - _Requirements: 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.6_

  - [x] 1.3 Implement Notification model
    - Create `apps/notifications/models.py` with the Notification model as specified in design (user FK, message text, is_read boolean, created_at, composite index)
    - Generate and apply migration
    - _Requirements: 13.1, 13.3, 13.4_

  - [x] 1.4 Implement GalleryImage model
    - Create `apps/gallery/models.py` with the GalleryImage model as specified in design (title, description, image with upload_to, is_published, uploaded_by FK with SET_NULL, ordering)
    - Generate and apply migration
    - _Requirements: 16.1, 16.2_

  - [x] 1.5 Implement ContactMessage model
    - Create `apps/contact/models.py` with the ContactMessage model as specified in design (name, email, subject, message, is_read, created_at, ordering)
    - Generate and apply migration
    - _Requirements: 17.2, 17.6, 17.7_

- [x] 2. Implement Pets app (forms, views, serializers, URLs)
  - [x] 2.1 Create Pet form and web views
    - Create `apps/pets/forms.py` with PetForm (ModelForm with image validation using `validate_image_file`)
    - Create `apps/pets/views.py` with ClientRequiredMixin-protected views: PetListView, PetCreateView, PetUpdateView, PetDeleteView
    - PetDeleteView must check for future reservations before allowing deletion
    - All views must filter queryset by `owner=request.user` for ownership isolation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.10, 7.11_

  - [x] 2.2 Create Pet serializer and API viewset
    - Create `apps/pets/serializers.py` with PetSerializer (all fields, read-only owner set from request.user)
    - Create `apps/pets/api_views.py` with PetViewSet (ModelViewSet, IsAuthenticated + client-only permission, queryset filtered by owner)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 21.1, 21.7, 21.8_

  - [x] 2.3 Configure Pet URLs
    - Update `apps/pets/urls.py` with web routes under client dashboard namespace
    - Add API routes: `api/v1/pets/` in root `urls.py` pointing to PetViewSet router
    - _Requirements: 7.2_

  - [ ]* 2.4 Write property tests for Pet models (Properties 1, 2, 3)
    - Create `apps/pets/tests/__init__.py` and `apps/pets/tests/test_pet_property.py`
    - **Property 1: Pet ownership isolation** — generate multiple users with pets, verify queryset filtering returns only owned pets
    - **Property 2: Pet weight validation** — generate decimals, verify accept/reject boundaries
    - **Property 3: Pet deletion with future reservations guard** — generate pets with/without future reservations, verify deletion logic
    - **Validates: Requirements 7.2, 7.5, 7.7, 7.4, 7.11**

- [x] 3. Implement Reservations app (forms, views, state machine, URLs)
  - [x] 3.1 Create Reservation form and client web views
    - Create `apps/reservations/forms.py` with ReservationForm (ModelForm, validate pet ownership and service availability in clean)
    - Create `apps/reservations/views.py` with ClientRequiredMixin-protected views: ReservationListView (filtered by client), ReservationCreateView, ReservationCancelView (checks ownership + pending status)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.9, 11.6, 11.7, 11.8, 12.1_

  - [x] 3.2 Create admin reservation web views
    - Add AdminRequiredMixin-protected views in `apps/reservations/views.py`: AdminReservationListView, ReservationApproveView, ReservationRejectView, ReservationCompleteView
    - All use `transition_to()` method for state enforcement
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 12.2_

  - [x] 3.3 Create Reservation serializer and API viewset
    - Create `apps/reservations/serializers.py` with ReservationSerializer (all fields, read-only client from request.user, validate pet ownership and service availability)
    - Create `apps/reservations/api_views.py` with ReservationViewSet (list/create/retrieve with role-based queryset, custom actions: cancel, approve, reject, complete)
    - Support status filtering via query parameter
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 21.1, 21.2_

  - [x] 3.4 Configure Reservation URLs
    - Update `apps/reservations/urls.py` with web routes for client and admin views
    - Add API routes: `api/v1/reservations/` in root `urls.py` pointing to ReservationViewSet router
    - _Requirements: 12.1, 12.2_

  - [ ]* 3.5 Write property tests for Reservations (Properties 8, 9, 10, 12, 13)
    - Create `apps/reservations/tests/__init__.py` and `apps/reservations/tests/test_reservation_property.py`
    - **Property 8: Reservation date validation** — generate date pairs, verify acceptance/rejection rules
    - **Property 9: Reservation creation validates pet ownership and service availability** — generate cross-client pet/service combos
    - **Property 10: Reservation state machine transitions** — generate all status/transition combos, verify ALLOWED_TRANSITIONS
    - **Property 12: Reservation visibility by role** — generate multi-client reservations, verify role-based filtering
    - **Property 13: Reservation status filtering** — generate reservations with various statuses, verify filter accuracy
    - **Validates: Requirements 10.4, 10.5, 10.2, 10.3, 11.1–11.4, 11.6, 11.7, 12.1, 12.2, 12.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Notifications app (signals, serializer, API)
  - [x] 5.1 Create notification signal handlers
    - Create `apps/notifications/signals.py` with `post_save` signal on Reservation model
    - On status change, create Notification for reservation's client with message containing pet name, service name, and new status
    - Register signal in `apps/notifications/apps.py` `ready()` method
    - _Requirements: 11.5, 13.1, 10.7_

  - [x] 5.2 Create Notification serializer and API viewset
    - Create `apps/notifications/serializers.py` with NotificationSerializer (id, message, is_read, created_at)
    - Create `apps/notifications/views.py` with NotificationViewSet: list (paginated, filtered by user), mark_read action (PATCH), unread_count action (GET)
    - Mark-read must be idempotent; queryset filtered by authenticated user
    - _Requirements: 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

  - [x] 5.3 Configure Notification URLs
    - Update `apps/notifications/urls.py` with DRF router under `api_notifications` namespace (already included in root urls.py)
    - _Requirements: 13.5_

  - [x]* 5.4 Write property tests for Notifications (Properties 11, 14, 15)
    - Create `apps/notifications/tests/__init__.py` and `apps/notifications/tests/test_notification_property.py`
    - **Property 11: Status change generates notification with correct content** — trigger transitions, verify notification created with pet name, service name, new status
    - **Property 14: Mark notification as read is idempotent** — mark read multiple times, verify always is_read=True
    - **Property 15: Unread notification count accuracy** — generate read/unread notifications, verify count endpoint
    - **Validates: Requirements 11.5, 13.1, 10.7, 13.3, 13.4**

- [x] 6. Implement Services app (views, serializer, API, admin CRUD)
  - [x] 6.1 Create Service serializer and API viewset
    - Create `apps/services/serializers.py` with ServiceSerializer (price as string with 2 decimals, all fields)
    - Create `apps/services/api_views.py` with ServiceViewSet (list available services, filter by category/availability, public read access)
    - _Requirements: 9.5, 9.6, 9.7, 21.1, 21.2, 21.6_

  - [x] 6.2 Create Service web views
    - Update `apps/services/views.py` with ServiceListView (public, filter by category, only is_available=True, ordered alphabetically)
    - Add admin views: ServiceAdminCreateView, ServiceAdminUpdateView, ServiceAdminDeleteView (all AdminRequiredMixin)
    - _Requirements: 8.1, 8.2, 8.3, 8.6, 8.7, 8.8, 8.9, 9.1, 9.2, 9.3, 9.4_

  - [x] 6.3 Configure Service URLs
    - Update `apps/services/urls.py` with public listing route and admin CRUD routes
    - Add API routes: `api/v1/services/` in root `urls.py` pointing to ServiceViewSet router
    - _Requirements: 9.1, 9.5_

  - [ ]* 6.4 Write property tests for Services (Properties 4, 5, 6, 7)
    - Create `apps/services/tests/__init__.py` and `apps/services/tests/test_service_property.py`
    - **Property 4: Service category enforcement** — generate arbitrary strings, verify only 7 valid categories accepted
    - **Property 5: Service price validation** — generate decimals, verify accept/reject boundaries (0.01–999999.99)
    - **Property 6: Service availability toggle is involutory** — toggle twice, verify restored value
    - **Property 7: Available services are alphabetically ordered and filtered** — generate services, verify ordering and category filtering
    - **Validates: Requirements 8.4, 8.5, 8.7, 9.2, 9.3**

- [x] 7. Implement Gallery app (views, admin management)
  - [x] 7.1 Create Gallery web views
    - Update `apps/gallery/views.py` with GalleryPublicView (public, only is_published=True, ordered by uploaded_at desc)
    - Add GalleryAdminUploadView (AdminRequiredMixin, validate image with `validate_image_file`, validate title/description lengths)
    - Add GalleryAdminDeleteView (AdminRequiredMixin, remove record and file)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_

  - [x] 7.2 Configure Gallery URLs
    - Update `apps/gallery/urls.py` with public gallery route and admin upload/delete routes
    - _Requirements: 16.1_

  - [ ]* 7.3 Write property test for Gallery (Property 17)
    - Create `apps/gallery/tests/__init__.py` and `apps/gallery/tests/test_gallery_property.py`
    - **Property 17: Gallery published filtering and ordering** — generate GalleryImage records with varying is_published, verify public view returns only published, ordered by uploaded_at desc
    - **Validates: Requirements 16.1**

- [x] 8. Implement Contact app (form, views, admin inbox)
  - [x] 8.1 Create Contact form and public view
    - Create `apps/contact/forms.py` with ContactForm (ModelForm, validate name ≤100, email format, subject ≤200, message ≤2000)
    - Update `apps/contact/views.py` with ContactPageView (GET renders form, POST validates and creates ContactMessage with is_read=False, shows success message)
    - _Requirements: 17.1, 17.2, 17.6, 17.7, 17.8_

  - [x] 8.2 Create Contact admin views
    - Add ContactAdminListView (AdminRequiredMixin, all messages ordered by created_at desc, show read/unread status)
    - Add ContactAdminDetailView (AdminRequiredMixin, marks message as read on access)
    - _Requirements: 17.3, 17.4, 17.5_

  - [x] 8.3 Configure Contact URLs
    - Update `apps/contact/urls.py` with public contact route and admin inbox routes
    - _Requirements: 17.1_

  - [ ]* 8.4 Write property tests for Contact (Properties 18, 19)
    - Create `apps/contact/tests/__init__.py` and `apps/contact/tests/test_contact_property.py`
    - **Property 18: Contact form field validation** — generate combinations of valid/invalid inputs, verify acceptance/rejection rules
    - **Property 19: Contact message creation sets is_read to False** — create messages, verify is_read=False always
    - **Validates: Requirements 17.6, 17.7, 17.2**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Dashboard app (admin KPIs, client summary)
  - [x] 10.1 Implement Client Dashboard view
    - Update `apps/dashboard/views.py` with ClientDashboardView (ClientRequiredMixin): display pet count, 5 most recent reservations
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 10.2 Implement Admin Dashboard view
    - Add AdminDashboardView (AdminRequiredMixin): compute KPIs (total users, total pets, active reservations, monthly revenue, most requested service)
    - Add admin management sections: paginated user list (20/page), pet list (20/page), reservation list with action buttons
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8_

  - [x] 10.3 Configure Dashboard URLs
    - Update `apps/dashboard/urls.py` with separate URL patterns for client and admin dashboard namespaces
    - Wire admin management sub-pages (users, pets, reservations, gallery, contact) into admin-panel URLs
    - _Requirements: 14.1, 15.1_

  - [ ]* 10.4 Write property tests for Dashboard KPIs (Property 16)
    - Create `apps/dashboard/tests/__init__.py` and `apps/dashboard/tests/test_dashboard_property.py`
    - **Property 16: Admin KPI calculations** — generate users/pets/reservations, verify total counts, active reservation count, monthly revenue sum, most requested service logic
    - **Validates: Requirements 14.1, 14.6, 14.7**

- [x] 11. Implement Public pages and Core views
  - [x] 11.1 Implement Home page and About page views
    - Update `apps/core/views.py` with HomePageView (display 3–6 featured services from Service model where is_available=True) and AboutPageView
    - Update `apps/core/urls.py` with routes for `/` and `/about/`
    - Wire core URLs into root `urls.py`
    - _Requirements: 18.1, 18.2, 18.7_

  - [x] 11.2 Create Django templates for all views
    - Create base template with Tailwind CSS + Alpine.js, responsive layout (sm/md/lg breakpoints)
    - Create templates for: home, about, services list, gallery, contact form, pet CRUD, reservation list/create, client dashboard, admin dashboard + management sections, notification display
    - Create error templates: `errors/403.html`, `errors/404.html`, `errors/500.html` (self-contained inline styles)
    - _Requirements: 18.6, 19.1, 19.2, 19.3, 19.4, 19.5_

- [x] 12. Wire API serialization, pagination, and filtering
  - [x] 12.1 Configure DRF settings and global pagination
    - Update Django settings with DRF configuration: default pagination class (PageNumberPagination, page_size=20, max_page_size=100), default filter backends (DjangoFilterBackend), default permission classes
    - _Requirements: 21.2, 21.3, 21.4, 21.5_

  - [x] 12.2 Add API routes to root URL configuration
    - Register all API viewset routers in root `urls.py`: pets, reservations, services
    - Verify notification API routes already configured
    - _Requirements: 21.1_

  - [ ]* 12.3 Write property tests for serialization (Properties 22, 23)
    - Create `apps/core/tests/test_serialization_property.py`
    - **Property 22: Serialization round-trip consistency** — serialize model instances, deserialize, verify field equivalence
    - **Property 23: Price serialization format** — generate Service instances, verify price serialized as string with exactly 2 decimal places
    - **Validates: Requirements 21.8, 21.6**

- [x] 13. Implement permissions and access control tests
  - [x] 13.1 Add DRF permission classes
    - Create `apps/core/permissions.py` with IsClient (allows only role=client), IsAdmin (allows only role=admin), IsOwner (checks object ownership)
    - Apply to all API viewsets: PetViewSet (IsClient), ReservationViewSet (IsAuthenticated with role-based logic), ServiceViewSet admin actions (IsAdmin), NotificationViewSet (IsAuthenticated + owner filtering)
    - _Requirements: 8.6, 10.8, 14.5, 16.4_

  - [ ]* 13.2 Write property test for permissions (Property 24)
    - Create `apps/core/tests/test_permissions_property.py`
    - **Property 24: Non-admin access denied for admin operations** — generate client/unauthenticated requests to admin-only endpoints, verify 403 responses
    - **Validates: Requirements 8.6, 14.5, 16.4**

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Existing code (CustomUser, Service, accounts app, core validators, JWT config, mixins) is reused throughout — do not re-implement
- All API endpoints use JWT authentication; all web views use session authentication
- The Reservation state machine (`transition_to()`) is the single source of truth for status changes across both web and API
- Signal-driven notifications decouple notification creation from reservation logic
- Templates use Tailwind CSS + Alpine.js per project conventions

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.4", "1.5"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "2.2", "6.1", "6.2", "7.1", "8.1", "8.2"] },
    { "id": 3, "tasks": ["2.3", "2.4", "3.1", "3.2", "6.3", "6.4", "7.2", "7.3", "8.3", "8.4"] },
    { "id": 4, "tasks": ["3.3", "3.4"] },
    { "id": 5, "tasks": ["3.5", "5.1"] },
    { "id": 6, "tasks": ["5.2", "5.3"] },
    { "id": 7, "tasks": ["5.4", "10.1", "10.2"] },
    { "id": 8, "tasks": ["10.3", "10.4", "11.1"] },
    { "id": 9, "tasks": ["11.2", "12.1", "12.2"] },
    { "id": 10, "tasks": ["12.3", "13.1"] },
    { "id": 11, "tasks": ["13.2"] }
  ]
}
```
