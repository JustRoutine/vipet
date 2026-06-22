# Implementation Plan: VIPET Luxury Pet Hotel Management Platform

## Overview

This plan converts the VIPET design document into an ordered sequence of coding tasks. Each task builds incrementally on the previous ones, starting from the Django project skeleton and finishing with deployment configuration. Property-based tests (Hypothesis) are included as optional sub-tasks tied directly to the ten correctness properties defined in the design.

---

## Tasks

- [x] 1. Project skeleton and configuration
  - [x] 1.1 Initialise the Django project and app layout
    - Run `django-admin startproject vipet .` inside the repo root
    - Create `vipet/settings/` package with `base.py`, `development.py`, `production.py`
    - Set `DJANGO_SETTINGS_MODULE` default to `vipet.settings.development` in `manage.py` and `wsgi.py`/`asgi.py`
    - Create `apps/` directory; register all eight app stubs (`accounts`, `pets`, `services`, `reservations`, `notifications`, `gallery`, `contact`, `dashboard`) with `apps.AppConfig` entries and add them to `INSTALLED_APPS` in `base.py`
    - Create a `core/` app stub inside `apps/` for shared mixins and validators
    - _Requirements: 18.1_

  - [x] 1.2 Configure MySQL, static/media paths, and third-party packages in settings
    - Add `mysqlclient` (or `PyMySQL`) `DATABASES` block to `base.py` reading credentials from environment variables via `python-decouple` or `os.getenv`
    - Configure `STATIC_URL`, `STATIC_ROOT`, `MEDIA_URL`, `MEDIA_ROOT` in `base.py`
    - Add `rest_framework`, `rest_framework_simplejwt`, `django_filters`, `cloudinary_storage` (conditional) to `INSTALLED_APPS`; configure `SIMPLE_JWT` settings block with 60-min access / 7-day refresh tokens
    - Configure Cloudinary switchable backend: if env vars present use `MediaCloudinaryStorage`, otherwise fall back to `FileSystemStorage`
    - Create `requirements.txt` with pinned versions: `Django>=5.0,<5.1`, `mysqlclient`, `djangorestframework`, `djangorestframework-simplejwt`, `django-filter`, `cloudinary`, `django-cloudinary-storage`, `Pillow`, `python-magic`, `hypothesis`, `pytest-django`, `pytest`, `python-decouple`
    - Add `tailwind.config.js` with brand colour tokens (`#FF007F`, `#1A1A1A`, `#FFFFFF`, `#FFE0EF`, `#666666`)
    - Create `.env.example` documenting all required env variables; add `.env` and `media/` to `.gitignore`
    - Create `pyproject.toml` with `[tool.pytest.ini_options]` and `[tool.hypothesis]` sections
    - _Requirements: 18.1, 18.2, 18.3, 18.6, 17.5_

  - [x] 1.3 Configure root URL file and error handlers
    - Wire `vipet/urls.py` with `include()` for each app namespace and the JWT token endpoints (`/api/v1/token/`, `/api/v1/token/refresh/`, `/api/v1/token/verify/`)
    - Set `handler403`, `handler404`, `handler500` in `vipet/urls.py` pointing to `apps.core.views`
    - Serve `MEDIA_ROOT` in development via `django.conf.urls.static.static()`
    - _Requirements: 16.1, 16.7_

- [x] 2. Core app — shared utilities
  - [x] 2.1 Implement custom access-control mixins
    - Create `apps/core/mixins.py` with `ClientRequiredMixin` and `AdminRequiredMixin` (both extend `UserPassesTestMixin`; return 403 on failure)
    - _Requirements: 16.2, 11.5, 12.4_

  - [x] 2.2 Implement image upload validator
    - Create `apps/core/validators.py` with `validate_image_file(file, max_size_mb)` using `python-magic` for MIME detection; raise `ValidationError` with specific reason for type violation and for size violation; read only the first 2 048 bytes for detection
    - _Requirements: 17.2, 17.3, 17.4_

  - [x] 2.3 Write property test for upload validation — Property 5 (MIME rejection)
    - **Property 5: Upload Validation Rejects All Non-Allowed MIME Types**
    - Use Hypothesis `@given` with strategies generating in-memory files with arbitrary MIME headers; assert `ValidationError` is raised for any non-jpeg/png/webp input and that no bytes reach storage
    - **Validates: Requirements 17.2, 17.4**

  - [x] 2.4 Write property test for upload validation — Property 6 (size rejection)
    - **Property 6: Upload Validation Rejects Files Exceeding Size Limit**
    - Use Hypothesis `@given` generating byte strings larger than the configured limit; assert `ValidationError` with size message is raised and nothing is written
    - **Validates: Requirements 17.3, 17.4**

  - [x] 2.5 Implement custom error handler views
    - Create `apps/core/views.py` with `handler403`, `handler404`, `handler500` rendering `errors/403.html`, `errors/404.html`, `errors/500.html`
    - Create corresponding minimal error templates
    - _Requirements: 16.2_

- [ ] 3. Checkpoint — Core app verified
  - Ensure all core tests pass and the dev server starts without errors. Ask the user if questions arise.

- [ ] 4. Accounts app
  - [x] 4.1 Implement `CustomUser` model and manager
    - Create `apps/accounts/models.py` with `CustomUser(AbstractBaseUser, PermissionsMixin)`: fields `id`, `email` (unique), `first_name`, `last_name`, `phone_number`, `role` (client/admin), `profile_photo`, `is_active`, `is_staff`, `date_joined`; `USERNAME_FIELD = "email"`; `REQUIRED_FIELDS = ["first_name", "last_name"]`
    - Implement `CustomUserManager` with `create_user` and `create_superuser` methods
    - Add `AUTH_USER_MODEL = "accounts.CustomUser"` to `base.py`
    - Create and apply initial migration
    - _Requirements: 1.1, 2.1, 2.2_

  - [ ] 4.2 Implement registration form and view
    - Create `apps/accounts/forms.py` — `RegistrationForm(ModelForm)` with `password` / `password2` fields; `clean_email` raises `ValidationError` on duplicate; `clean` validates password match; password min 8 / max 128 chars
    - Create `RegisterView(FormView)` in `apps/accounts/views.py`; on valid form call `user.set_password()` and save; redirect to login
    - Wire URL `/accounts/register/` → `accounts:register`
    - Create `templates/accounts/register.html` with CSRF token and field-level error display
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 4.3 Implement login and logout views
    - Create `LoginView(FormView)` with `authenticate()` + `login()`; redirect `admin` → `/admin-panel/`, `client` → `/client/`; on invalid credentials show form error
    - Implement login-attempt rate limiting (5 failures / 15 min per IP) using Django's cache framework
    - If authenticated user visits `/accounts/login/` or `/accounts/register/`, redirect to role dashboard
    - Create `LogoutView(View)` calling `logout()` and redirecting to `/`
    - Create `templates/accounts/login.html`
    - Wire URLs `/accounts/login/`, `/accounts/logout/`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 13.7_

  - [x] 4.4 Implement password reset flow
    - Create `PasswordResetRequestView` and `PasswordResetConfirmView` using `PasswordResetTokenGenerator`; set `PASSWORD_RESET_TIMEOUT = 3600` in `base.py`
    - Show same confirmation message whether email is registered or not (no enumeration)
    - Invalidate token after first use
    - Create templates `password_reset.html` and `password_reset_confirm.html`
    - Wire URLs `/accounts/password-reset/` and `/accounts/password-reset/<uidb64>/<token>/`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 4.5 Implement profile view and form
    - Create `ProfileUpdateForm(ModelForm)` with fields `first_name`, `last_name`, `phone_number`, `profile_photo`; call `validate_image_file` in `clean_profile_photo` (max 5 MB)
    - Create `ProfileView(LoginRequiredMixin, UpdateView)` — email is read-only; show success message on save; show default avatar if no photo
    - Wire URL `/accounts/profile/`
    - Create `templates/accounts/profile.html`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 4.6 Write unit tests for accounts app
    - Test valid registration creates user with hashed password
    - Test duplicate email rejected with field error
    - Test password mismatch rejected
    - Test short/long password rejected
    - Test admin login redirects to `/admin-panel/`, client to `/client/`
    - Test invalid credentials show error
    - Test logout invalidates session
    - Test password reset token expires after 60 min
    - Test token cannot be reused
    - _Requirements: 1.1–1.6, 2.1–2.5, 3.1–3.4_

- [ ] 5. Pets app
  - [ ] 5.1 Implement `Pet` model and migration
    - Create `apps/pets/models.py` — `Pet` with all fields from design; `owner` FK to `CustomUser`; index on `owner`, `species`
    - Create and apply migration
    - _Requirements: 5.1_

  - [ ] 5.2 Implement pet form and CRUD views
    - Create `apps/pets/forms.py` — `PetForm(ModelForm)` with `clean_age` (0–30) and `clean_weight` (0.1–200); call `validate_image_file` in `clean_photo` (max 5 MB)
    - Create `PetListView`, `PetCreateView`, `PetUpdateView`, `PetDeleteView` — all guarded by `LoginRequiredMixin + ClientRequiredMixin`; `PetDeleteView` checks for active reservations (Pending/Approved) before deletion and shows error if found; owner-scoped queryset on all views
    - Wire URLs under `/client/pets/`
    - Create templates `dashboard/client/pets.html` and `dashboard/client/pets_form.html`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ] 5.3 Write property test for pet deletion — Property 7
    - **Property 7: Pet Deletion Blocked When Active Reservations Exist**
    - Use Hypothesis to generate pets with arbitrary combinations of reservation statuses; assert deletion is rejected when any reservation is Pending/Approved and succeeds otherwise
    - **Validates: Requirements 5.4**

  - [ ] 5.4 Write unit tests for pets app
    - Test pet creation success and failure edge cases (boundary age, weight values)
    - Test pet photo upload rejection for invalid MIME and oversized file
    - Test owner cannot see or delete another client's pet
    - _Requirements: 5.1–5.7_

- [ ] 6. Services app
  - [ ] 6.1 Implement `Service` model and migration
    - Create `apps/services/models.py` with all fields and `CATEGORY_CHOICES`; index on `is_available`, `category`
    - Create and apply migration
    - _Requirements: 6.1, 6.2_

  - [ ] 6.2 Implement service views (admin CRUD + public listing)
    - Create public `ServiceListView(ListView)` returning only `is_available=True` services; empty-state on no results
    - Create `AdminServiceListView`, `AdminServiceCreateView`, `AdminServiceUpdateView`, `AdminServiceDeleteView` — all guarded by `AdminRequiredMixin`; `ServiceForm` calls `validate_image_file` in `clean_image` (max 5 MB)
    - Wire public URL `/services/` and admin URLs under `/admin-panel/services/`
    - Create `templates/public/services.html` and admin service templates
    - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6, 6.7, 13.3_

  - [ ] 6.3 Write unit tests for services app
    - Test service creation, update, unavailability flag
    - Test that unavailable services do not appear in the reservation form queryset
    - Test image upload rejection for invalid MIME / oversized file
    - _Requirements: 6.1–6.7_

- [ ] 7. Reservations app
  - [ ] 7.1 Implement `Reservation` model and migration
    - Create `apps/reservations/models.py` — all fields from design; `STATUS_CHOICES` and `ALLOWED_TRANSITIONS`; indexes on `client`, `status`, `start_date`, `created_at`
    - Create and apply migration
    - _Requirements: 7.1_

  - [ ] 7.2 Implement price calculation utility
    - Create `apps/reservations/utils.py` — `calculate_total_price(service, start_date, end_date)` returning `service.price × Decimal(days)`
    - _Requirements: 7.1_

  - [ ] 7.3 Write property test for price calculation — Property 1
    - **Property 1: Total Price Calculation Is Consistent**
    - Use Hypothesis `@given` with `st.decimals()` for price and `st.dates()` for date pairs (end > start); assert `result == price × days` and result is non-negative
    - **Validates: Requirements 7.1**

  - [ ] 7.4 Implement reservation state machine service
    - Create `apps/reservations/services.py` — `transition_reservation(reservation, new_status, actor)` enforcing `ALLOWED_ADMIN_TRANSITIONS` and `ALLOWED_CLIENT_CANCELLATION`; raises `ValueError` on invalid transition; calls `_create_notification()` on success
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 8.2, 8.3_

  - [ ] 7.5 Write property test for state machine — Property 2
    - **Property 2: Reservation Status Transition Validity**
    - Use Hypothesis to generate all combinations of (current_status, new_status, actor_role); assert `ValueError` is raised for every disallowed transition and status is unchanged
    - **Validates: Requirements 9.5**

  - [ ] 7.6 Implement reservation form and client views
    - Create `ReservationCreateForm(ModelForm)` — pet queryset filtered to `owner=user`; service queryset filtered to `is_available=True`; `clean` validates start_date ≥ today and end_date > start_date; auto-sets `total_price` from `calculate_total_price` in `form_valid`
    - Create `ReservationListView` (reverse-chron by start_date), `ReservationCreateView`, `ReservationCancelView` — all guarded by `LoginRequiredMixin + ClientRequiredMixin`; `CancelView` calls `transition_reservation` with `"cancelled"` and catches `ValueError`
    - Show empty-state with link to services if no reservations; show message with link to add-pet page if no pets
    - Wire client URLs under `/client/reservations/`
    - Create templates `dashboard/client/reservations.html` and `dashboard/client/reservations_form.html`
    - _Requirements: 7.1–7.6, 8.1–8.5_

  - [ ] 7.7 Implement admin reservation views and filters
    - Create `apps/reservations/filters.py` — `ReservationFilter(FilterSet)` for status / start_date / end_date
    - Create `AdminReservationListView` (sorted by `created_at` desc, supports filter), `AdminReservationUpdateView` — guarded by `AdminRequiredMixin`; update view calls `transition_reservation` and catches `ValueError`; display error on invalid transition
    - Wire admin URLs under `/admin-panel/reservations/`
    - Create templates `dashboard/admin/reservations.html` and `dashboard/admin/reservation_detail.html`
    - _Requirements: 9.1–9.5_

  - [ ] 7.8 Write unit tests for reservations app
    - Test valid reservation creation sets status=pending and correct total_price
    - Test past start date rejected; end date ≤ start date rejected
    - Test unavailable service blocked
    - Test client cancel of pending/approved succeeds; cancel of terminal state fails
    - Test admin approve/reject/complete transitions with notification side-effects
    - Test invalid admin transitions return error and leave status unchanged
    - _Requirements: 7.1–7.6, 8.1–8.5, 9.1–9.5_

- [ ] 8. Checkpoint — Core domain logic verified
  - Ensure all reservation, pet, and service tests pass. Ask the user if questions arise.

- [ ] 9. Notifications app
  - [ ] 9.1 Implement `Notification` model and migration
    - Create `apps/notifications/models.py` — fields `id`, `user` FK, `reservation` FK, `message`, `is_read`, `created_at`; indexes on `user`, `is_read`, `created_at`
    - Verify that `_create_notification()` in `reservations/services.py` imports and uses this model correctly
    - Create and apply migration
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 9.2 Implement notification serializer and REST API views
    - Create `apps/notifications/serializers.py` — `NotificationSerializer` with `pet_name` and `service_name` `SerializerMethodField`s
    - Create `apps/notifications/api_views.py` — `NotificationListAPIView`, `NotificationMarkReadAPIView` (PATCH `is_read=True`), `UnreadCountAPIView`; all require `IsAuthenticated`; queryset filtered to `request.user`
    - Wire API URLs under `/api/v1/notifications/`
    - _Requirements: 10.4, 10.5, 10.6_

  - [ ] 9.3 Implement notification list template view
    - Create `NotificationListView(LoginRequiredMixin, ClientRequiredMixin, ListView)` at `/client/notifications/`
    - Create `templates/dashboard/client/notifications.html` — reverse-chron order; visually distinguish read vs unread
    - _Requirements: 10.4_

  - [ ] 9.4 Write property test for notification creation on valid transitions — Property 3
    - **Property 3: Notification Created on Every Valid Status Transition**
    - Use Hypothesis to generate reservations and apply every valid admin transition; assert exactly one `Notification` is created per transition to Approved/Rejected/Completed and unread count increases by exactly 1
    - **Validates: Requirements 10.1, 10.2, 10.3**

  - [ ] 9.5 Write property test for notification read/unread round trip — Property 4
    - **Property 4: Notification Read/Unread Round Trip**
    - Use Hypothesis to generate a client with N (1–50) unread notifications; mark one as read; assert unread count = N−1; mark an already-read notification; assert count unchanged
    - **Validates: Requirements 10.5, 10.6**

  - [ ] 9.6 Write unit tests for notifications app
    - Test notification created on reservation approval, rejection, completion
    - Test no notification created on client cancellation
    - Test `UnreadCountAPIView` returns correct count
    - Test `NotificationMarkReadAPIView` sets `is_read=True`; idempotent on already-read
    - Test unauthenticated request to API returns 401
    - _Requirements: 10.1–10.6_

- [ ] 10. Gallery app
  - [ ] 10.1 Implement `GalleryImage` model and migration
    - Create `apps/gallery/models.py` — `GalleryCategory(TextChoices)` and `GalleryImage` with `title`, `category`, `image`, `created_at`; index on `category`
    - Create and apply migration
    - _Requirements: 14.1, 14.2_

  - [ ] 10.2 Implement gallery views (public + admin)
    - Create `GalleryPublicView(ListView)` at `/gallery/` grouping images by category; empty-state if no images
    - Create `AdminGalleryListView`, `AdminGalleryCreateView` (validates image via `validate_image_file` with 10 MB limit), `AdminGalleryDeleteView` — all guarded by `AdminRequiredMixin`
    - Wire public URL `/gallery/` and admin URLs under `/admin-panel/gallery/`
    - Create `templates/public/gallery.html` and admin gallery templates
    - _Requirements: 14.1–14.4, 13.5_

  - [ ] 10.3 Write unit tests for gallery app
    - Test upload stores image and returns 200 on public page
    - Test deletion removes image from page within one request cycle
    - Test oversized or invalid-MIME image rejected
    - _Requirements: 14.1–14.4_

- [ ] 11. Contact app
  - [ ] 11.1 Implement `ContactMessage` model and migration
    - Create `apps/contact/models.py` — fields `id`, `name`, `email`, `subject`, `message`, `submitted_at`; index on `submitted_at`
    - Create and apply migration
    - _Requirements: 15.1_

  - [ ] 11.2 Implement contact form view and admin inbox
    - Create `ContactMessageForm(ModelForm)` with all four required fields; whitespace-only values must fail validation (`strip=True` on `CharField`)
    - Create `ContactFormView(FormView)` — `form_valid` wraps `save()` in try/except `DatabaseError`; show success message; show error preserving data on DB failure
    - Create `AdminContactListView(AdminRequiredMixin, ListView)` at `/admin-panel/contact/` sorted by `submitted_at` desc
    - Wire URLs `/contact/` and `/admin-panel/contact/`
    - Create `templates/public/contact.html` and `templates/dashboard/admin/contact.html`
    - _Requirements: 15.1–15.4, 13.6_

  - [ ] 11.3 Write property test for whitespace rejection — Property 8
    - **Property 8: Whitespace-Only and Empty Inputs Are Rejected by Validation**
    - Use Hypothesis `@given(st.text(alphabet=string.whitespace, min_size=1))` for each minimum-length-1 form field; assert `form.is_valid() == False` and model record is not created
    - **Validates: Requirements 1.5, 15.2**

  - [ ] 11.4 Write unit tests for contact app
    - Test valid submission saves record and shows success
    - Test missing/empty fields show field-level errors and preserve other values
    - Test DB failure shows error and preserves data
    - _Requirements: 15.1–15.4_

- [ ] 12. Dashboard app
  - [ ] 12.1 Implement admin dashboard statistics view
    - Create `apps/dashboard/views.py` — `get_admin_stats()` function (total clients, total pets, active reservations count, monthly revenue sum of completed reservations, top service by monthly booking count with alphabetical tie-break)
    - Create `AdminDashboardHomeView(AdminRequiredMixin, TemplateView)` at `/admin-panel/`
    - Create admin user list view with `UserFilter` (email, date_joined range); admin pets list view with species/owner-email filter; admin services list at `/admin-panel/services/`
    - Create `templates/dashboard/admin/home.html` with stat widgets
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ] 12.2 Write property test for monthly revenue — Property 10
    - **Property 10: Monthly Revenue Is Sum of Completed Reservations in Current Month**
    - Use Hypothesis to generate arbitrary sets of reservations with varied statuses and end_dates; assert `get_admin_stats()["monthly_revenue"]` equals the exact sum of `total_price` for completed reservations ending in the current month
    - **Validates: Requirements 11.1**

  - [ ] 12.3 Implement client dashboard home view
    - Create `get_client_stats(user)` helper returning pet count, active reservation count (Pending/Approved), unread notification count
    - Create `ClientDashboardHomeView(LoginRequiredMixin, ClientRequiredMixin, TemplateView)` at `/client/`; displays zeros rather than hiding widgets when counts are zero; shows unread notification badge
    - Create `templates/dashboard/client/home.html`
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 12.4 Write property test for client data isolation — Property 9
    - **Property 9: Client Data Isolation**
    - Use Hypothesis to generate two distinct client users and associated pets/reservations; assert every cross-client GET/POST request returns 403 and no data is modified
    - **Validates: Requirements 12.4, 16.2**

  - [ ] 12.5 Write unit tests for dashboard app
    - Test admin stat calculations: revenue includes only completed reservations in current month; top service alphabetical tie-break
    - Test non-admin access to admin views returns 403
    - Test client dashboard shows zero counts correctly
    - _Requirements: 11.1–11.5, 12.1–12.4_

- [ ] 13. Checkpoint — All app logic and tests passing
  - Ensure full pytest run passes. Ask the user if questions arise.

- [ ] 14. Templates, Tailwind, and Alpine.js
  - [ ] 14.1 Build base and dashboard layout templates
    - Create `templates/base.html` — loads `output.css`, Google Fonts (Bodoni Moda + Jost), Alpine.js CDN, and `app.js`; `x-data="vipetApp()"` on `<html>`
    - Create `templates/base_dashboard.html` — extends `base.html`; sidebar layout block
    - Create `templates/components/navbar.html` — public nav with brand colours; login/register CTA; notification badge slot
    - Create `templates/components/dashboard_sidebar_admin.html` and `dashboard_sidebar_client.html`
    - Create `templates/components/footer.html`, `flash_messages.html`, `pet_card.html`, `notification_badge.html`
    - _Requirements: 18.3, 18.4, 18.5_

  - [ ] 14.2 Build public website page templates
    - Create `templates/public/home.html` — hero, VIPET story, featured services, "Why Choose VIPET", testimonials, pricing overview, contact section, footer
    - Create `templates/public/about.html` — mission and story sections
    - Create `templates/public/pricing.html` — available service prices; empty-state if none
    - Update `templates/public/services.html`, `gallery.html`, `contact.html` with final Tailwind styling
    - Wire public views in `apps/` (or a `public` app/module) to URLs `/`, `/about/`, `/pricing/`
    - _Requirements: 13.1–13.6, 13.8_

  - [ ] 14.3 Implement Alpine.js notification badge component
    - Write `static/js/app.js` — `vipetApp()` with `unreadCount`, `init()` polling every 60 s, `fetchUnreadCount()`, `markRead(notificationId)`
    - Integrate badge into `notification_badge.html` using `x-show`, `x-text` directives; hide badge when `unreadCount === 0`
    - Store/retrieve JWT access token from `localStorage`
    - _Requirements: 10.5, 10.6, 12.3, 18.5_

  - [ ] 14.4 Compile Tailwind CSS
    - Create `static/css/input.css` with `@tailwind base/components/utilities` directives
    - Run `npx tailwindcss -i static/css/input.css -o static/css/output.css --minify` and commit `output.css`
    - Ensure `tailwind.config.js` `content` array covers all HTML template paths
    - _Requirements: 18.3_

- [ ] 15. Security hardening
  - [ ] 15.1 Apply production security settings
    - In `vipet/settings/production.py` set: `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`, `SECURE_HSTS_PRELOAD=True`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, `X_FRAME_OPTIONS="DENY"`, `SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_HTTPONLY=True`
    - _Requirements: 16.4, 16.5_

  - [ ] 15.2 Verify CSRF tokens in all POST forms
    - Audit every template with a POST form to confirm `{% csrf_token %}` is present
    - Confirm DRF views use `JWTAuthentication` (CSRF not required) or `SessionAuthentication` (CSRF enforced)
    - _Requirements: 16.5_

  - [ ] 15.3 Verify JWT settings and API access control
    - Confirm `SIMPLE_JWT` block has `ACCESS_TOKEN_LIFETIME=timedelta(minutes=60)` and `REFRESH_TOKEN_LIFETIME=timedelta(days=7)`
    - Confirm all `/api/v1/` views have `permission_classes = [IsAuthenticated]`; unauthenticated requests return 401
    - _Requirements: 16.3, 16.6_

- [ ] 16. Media storage
  - [ ] 16.1 Configure upload paths and switchable backend
    - Verify `upload_to` values: `profiles/`, `pets/`, `services/`, `gallery/`
    - Verify Cloudinary switching logic in `base.py` — when env vars present, `DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"`; otherwise local `FileSystemStorage`
    - Verify `validate_image_file` is called in every model form that handles image uploads (profile, pet, service, gallery)
    - _Requirements: 17.1, 17.5_

  - [ ] 16.2 Write unit tests for media storage
    - Test that valid JPEG/PNG/WebP files under the size limit are accepted by each form
    - Test that invalid MIME type and oversized files are rejected with correct error messages
    - Test `DEFAULT_FILE_STORAGE` switches correctly based on env vars (mock `os.getenv`)
    - _Requirements: 17.1–17.5_

- [ ] 17. Deployment configuration
  - [ ] 17.1 Create production-ready deployment files
    - Create `Procfile` (Gunicorn) and `runtime.txt` (Python 3.11)
    - Create `vipet/settings/production.py` with all security settings, `ALLOWED_HOSTS`, `DEBUG=False`, `STATICFILES_DIRS`, `STATIC_ROOT`
    - Add `collectstatic` step documentation in `README.md`
    - Create `README.md` with: local setup (venv, .env, migrate, tailwind build, runserver), environment variable reference, deployment checklist
    - _Requirements: 18.1, 16.4_

  - [ ] 17.2 Final checkpoint — Full test suite and deployment readiness
    - Run full `pytest` suite; all tests must pass
    - Verify `python manage.py check --deploy` produces no critical warnings
    - Ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout the build
- Property tests (Properties 1–10) validate universal correctness guarantees defined in the design document; unit tests validate specific examples and edge cases
- The `core` app must be implemented before any other app since it supplies shared mixins and validators
- All image upload forms must call `validate_image_file` from `apps.core.validators` — this is the single enforcement point for Requirements 17.2–17.4
- Tailwind output.css must be committed (or built as part of CI) so the app renders correctly without a Node build step at runtime

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.5"] },
    { "id": 3, "tasks": ["2.3", "2.4", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "4.5", "6.1"] },
    { "id": 5, "tasks": ["4.6", "5.1", "6.2"] },
    { "id": 6, "tasks": ["5.2", "6.3", "7.1", "9.1", "10.1", "11.1"] },
    { "id": 7, "tasks": ["5.3", "5.4", "7.2"] },
    { "id": 8, "tasks": ["7.3", "7.4"] },
    { "id": 9, "tasks": ["7.5", "7.6"] },
    { "id": 10, "tasks": ["7.7", "9.2", "9.3", "10.2", "11.2"] },
    { "id": 11, "tasks": ["7.8", "9.4", "9.5", "9.6", "10.3", "11.3", "11.4", "12.1"] },
    { "id": 12, "tasks": ["12.2", "12.3"] },
    { "id": 13, "tasks": ["12.4", "12.5", "14.1"] },
    { "id": 14, "tasks": ["14.2", "14.3", "15.1", "15.2", "15.3", "16.1"] },
    { "id": 15, "tasks": ["14.4", "16.2"] },
    { "id": 16, "tasks": ["17.1"] },
    { "id": 17, "tasks": ["17.2"] }
  ]
}
```
