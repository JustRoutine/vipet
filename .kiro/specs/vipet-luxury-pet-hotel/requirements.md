# Requirements Document

## Introduction

VIPET is a luxury pet hotel management web application that enables pet owners to register accounts, manage their pets' profiles, browse premium services, and make reservations. Administrators have full control over users, services, reservations, and platform content. The platform is built with Python 3, Django 5, MySQL, and Tailwind CSS, offering a polished and branded experience consistent with VIPET's luxury identity.

The system supports two roles: **Administrator** and **Client (Pet Owner)**. It includes a public-facing website, authenticated dashboards for both roles, a notification system, a gallery module, and a contact module.

---

## Glossary

- **System**: The VIPET web application
- **Client**: A registered pet owner user of the platform
- **Administrator**: A privileged user who manages the platform, services, reservations, and users
- **Pet**: An animal profile owned by a Client, containing health and identification information
- **Service**: A hotel offering (e.g., Luxury Suite, Grooming, Spa) managed by the Administrator
- **Reservation**: A booking made by a Client for a specific Pet and Service with a defined date range
- **Notification**: An in-app message delivered to a Client when a Reservation status changes
- **Dashboard**: The authenticated management interface available to both Clients and Administrators
- **Gallery**: A public-facing collection of images showcasing the hotel facilities and services
- **Contact_Form**: A form through which visitors submit messages to the Administrator
- **JWT**: JSON Web Token used for stateless authentication
- **Media_Storage**: Local file storage for uploaded images, prepared for migration to Cloudinary
- **Reservation_Status**: One of five states: Pending, Approved, Rejected, Completed, Cancelled

---

## Requirements

---

### Requirement 1: User Registration

**User Story:** As a visitor, I want to create an account, so that I can access the VIPET platform as a Client.

#### Acceptance Criteria

1. WHEN a visitor submits a registration form with a first name (1–50 characters), last name (1–50 characters), valid email address (local-part@domain format), phone number (8–15 digits with optional country code prefix), and password (8–128 characters), THE System SHALL create a new Client account and redirect the visitor to the login page.
2. WHEN a visitor submits a registration form with an email address that already exists in the database, THE System SHALL display an inline error message on the email field indicating that the email is already registered, and SHALL preserve all other submitted field values on the form.
3. IF a visitor submits a registration form with a password shorter than 8 characters or longer than 128 characters, THEN THE System SHALL display a field-level validation error message on the password field without creating the account.
4. IF a visitor submits a registration form with mismatched password and password confirmation fields, THEN THE System SHALL display a validation error on the password confirmation field and prevent account creation.
5. IF a visitor submits a registration form with any required field missing or containing an invalid format, THEN THE System SHALL display a field-level validation error for each invalid field and prevent account creation.
6. THE System SHALL store passwords in a non-recoverable hashed form such that the original password cannot be retrieved from the stored value.

---

### Requirement 2: User Authentication

**User Story:** As a registered user, I want to log in and out securely, so that I can access my personal dashboard.

#### Acceptance Criteria

1. WHEN a Client submits valid credentials (email and password), THE System SHALL authenticate the user and redirect them to the Client Dashboard.
2. WHEN an Administrator submits valid credentials, THE System SHALL authenticate the user and redirect them to the Administrator Dashboard.
3. WHEN a user submits invalid credentials, THE System SHALL display an error message and deny access.
4. WHEN an authenticated user clicks "Logout", THE System SHALL invalidate the session and redirect the user to the public home page.
5. THE System SHALL limit failed login attempts to 5 consecutive failures per IP address within a 15-minute window, after which THE System SHALL temporarily block further attempts from that IP.

---

### Requirement 3: Password Reset

**User Story:** As a registered user, I want to reset my forgotten password, so that I can regain access to my account.

#### Acceptance Criteria

1. WHEN a user submits a registered email address on the password reset page, THE System SHALL send a password reset email containing a time-limited token link (valid for 60 minutes) to that address. IF the submitted email address is not registered, THE System SHALL display the same confirmation message as for a registered address to prevent user enumeration.
2. WHEN a user follows a valid, unexpired password reset link and submits a new password between 8 and 128 characters, THE System SHALL update the password, invalidate any previously issued reset tokens for that account, and redirect the user to the login page.
3. WHEN a user follows an expired or invalid password reset link, THE System SHALL display an error message and prompt the user to request a new reset link.
4. THE System SHALL invalidate a password reset token after it has been used once.

---

### Requirement 4: Profile Management

**User Story:** As a registered user, I want to view and update my profile information, so that my account details remain accurate.

#### Acceptance Criteria

1. WHEN an authenticated user navigates to their profile page, THE System SHALL display their current first name, last name, email address, phone number, and profile photo (or a default avatar if no photo has been uploaded).
2. WHEN an authenticated user submits updated profile information where first name and last name are 1–50 characters and phone number is 7–15 digits, THE System SHALL save the changes and display a success confirmation message. The email address field SHALL be read-only and not modifiable via this form.
3. WHEN an authenticated user uploads a profile photo in JPEG, PNG, or WebP format not exceeding 5 MB, THE System SHALL store the image in Media_Storage under the profiles/ subdirectory and display it on the profile page.
4. IF an authenticated user uploads a file that is not JPEG, PNG, or WebP, or exceeds 5 MB, THEN THE System SHALL reject the upload and display an error message specifying whether the rejection was due to an invalid format or the size limit being exceeded.
5. WHEN an authenticated user has not uploaded a profile photo, THE System SHALL display a default avatar placeholder on the profile page.

---

### Requirement 5: Pet Management

**User Story:** As a Client, I want to add, view, edit, and delete my pets' profiles, so that I can manage their information for reservations.

#### Acceptance Criteria

1. WHEN an authenticated Client submits a new pet form with a name (1–100 characters), species, breed, gender (one of: Male, Female), age (0–30 years, whole number), and weight (0.1–200 kg), THE System SHALL create a Pet record linked to the Client's account.
2. WHEN an authenticated Client navigates to "My Pets", THE System SHALL display a list of all Pet records associated with the Client's account.
3. WHEN an authenticated Client submits updated information for an existing Pet, including name, species, breed, gender, age, weight, medical notes, and vaccination status, THE System SHALL save the changes and display a success message.
4. WHEN an authenticated Client confirms deletion of a Pet that has no active (Pending or Approved) Reservations, THE System SHALL permanently remove the Pet record from the database. IF the Pet has one or more active Reservations, THEN THE System SHALL display an error message indicating the Pet cannot be deleted while active reservations exist.
5. WHEN an authenticated Client uploads a pet photo in JPEG, PNG, or WebP format not exceeding 5 MB, THE System SHALL store the image in Media_Storage under the pets/ subdirectory and associate it with the Pet record.
6. IF an authenticated Client uploads a file that is not JPEG, PNG, or WebP, or exceeds 5 MB, THEN THE System SHALL reject the upload and display an error message.
7. THE System SHALL allow a Client to optionally record medical notes (up to 2000 characters) and a vaccination status (vaccinated: true/false) for each Pet.

---

### Requirement 6: Service Management (Administrator)

**User Story:** As an Administrator, I want to create, edit, and manage hotel services, so that Clients can browse and book them.

#### Acceptance Criteria

1. WHEN an Administrator submits a new service form with a name (1–100 characters), description (1–1000 characters), price (0.01–9999.99 MAD), and availability status, THE System SHALL create a Service record in the database.
2. THE System SHALL support the following service categories: Luxury Suite, Grooming, Spa, Daycare, Training, Veterinary Checkup, and Birthday Events.
3. WHEN an Administrator submits an update to a Service record with valid name, description, price, and availability values, THE System SHALL persist the changes so that subsequent reads of the Service record reflect the updated values.
4. WHEN an Administrator marks a Service as unavailable, THE System SHALL prevent Clients from selecting that Service when creating a new Reservation.
5. WHEN an Administrator uploads a service image in JPEG, PNG, or WebP format not exceeding 5 MB, THE System SHALL store it in Media_Storage under the services/ subdirectory and associate it with the Service.
6. IF an Administrator uploads a service image that is not JPEG, PNG, or WebP, or exceeds 5 MB, THEN THE System SHALL reject the upload and display an error message specifying whether the rejection is due to invalid format or size exceeded.
7. THE System SHALL display the current price and availability status of each Service on the public Services page.

---

### Requirement 7: Reservation Creation

**User Story:** As a Client, I want to create a reservation for my pet, so that I can book a hotel service.

#### Acceptance Criteria

1. WHEN an authenticated Client submits a reservation form with a valid Pet, an available Service, a start date on or after today's calendar date, and an end date at least one day after the start date, THE System SHALL create a Reservation record with a status of Pending and set the Total Price to the Service's daily price multiplied by the number of whole days between the start date and the end date (end date minus start date).
2. IF a Client selects a start date earlier than today's calendar date, THEN THE System SHALL display a validation error on the start date field and prevent form submission.
3. IF a Client selects an end date equal to or earlier than the start date, THEN THE System SHALL display a validation error on the end date field and prevent form submission.
4. IF a Client attempts to create a reservation for a Service marked as unavailable, THEN THE System SHALL display an error message indicating the service is unavailable and prevent the reservation from being created.
5. THE System SHALL allow Clients to add optional notes (up to 500 characters) to a Reservation at the time of creation.
6. IF an authenticated Client has no registered Pets, THEN THE System SHALL display a message on the reservation creation page indicating that a Pet must be added before a reservation can be created, and SHALL provide a link to the Add Pet page.

---

### Requirement 8: Reservation Management (Client)

**User Story:** As a Client, I want to view and cancel my reservations, so that I can manage my bookings.

#### Acceptance Criteria

1. WHEN an authenticated Client navigates to "My Reservations", THE System SHALL display a list of all Reservations associated with the Client, showing Pet name, Service name, start date, end date, total price, and current status.
2. WHEN an authenticated Client cancels a Reservation with a status of Pending or Approved, THE System SHALL update the Reservation status to Cancelled and immediately reflect the updated status in the displayed reservations list.
3. IF an authenticated Client attempts to cancel a Reservation with a status of Completed, Rejected, or Cancelled, THEN THE System SHALL display an error message and prevent the cancellation.
4. WHEN an authenticated Client views "My Reservations", THE System SHALL display the list in reverse chronological order by start date (most recent start date first).
5. WHEN an authenticated Client has no reservations, THE System SHALL display an empty-state message indicating no reservations have been made and providing a link to browse available services.

---

### Requirement 9: Reservation Management (Administrator)

**User Story:** As an Administrator, I want to approve, reject, and complete reservations, so that I can control the hotel's booking pipeline.

#### Acceptance Criteria

1. WHEN an Administrator views the reservations list, THE System SHALL display all Reservations across all Clients sorted by creation date descending, showing current status, Client name, Pet name, Service name, date range, and total price.
2. WHEN an Administrator approves a Pending Reservation, THE System SHALL update the Reservation status to Approved and trigger a notification to the Client.
3. WHEN an Administrator rejects a Pending or Approved Reservation, THE System SHALL update the Reservation status to Rejected and trigger a notification to the Client.
4. WHEN an Administrator marks an Approved Reservation as completed, THE System SHALL update the Reservation status to Completed and trigger a notification to the Client.
5. IF an Administrator attempts a status transition not defined in the allowed state machine (Pending → Approved or Rejected; Approved → Completed or Rejected; Rejected, Completed, Cancelled are terminal states), THEN THE System SHALL display an error message and leave the Reservation status unchanged.

---

### Requirement 10: Notification System

**User Story:** As a Client, I want to receive notifications when my reservation status changes, so that I am informed of booking updates.

#### Acceptance Criteria

1. WHEN a Reservation status changes to Approved, THE System SHALL create an in-app Notification for the corresponding Client containing the pet name, service name, and the message that the reservation has been approved.
2. WHEN a Reservation status changes to Rejected, THE System SHALL create an in-app Notification for the corresponding Client containing the pet name, service name, and the message that the reservation has been rejected.
3. WHEN a Reservation status changes to Completed, THE System SHALL create an in-app Notification for the corresponding Client containing the pet name, service name, and the message that the service has been completed.
4. WHEN an authenticated Client views the notifications panel, THE System SHALL display all Notifications for the Client in reverse chronological order, with unread notifications visually distinguished from read notifications.
5. WHEN a Client clicks a Notification, THE System SHALL mark that Notification as read and decrement the unread count displayed in the navigation badge.
6. WHEN an authenticated Client has no unread Notifications, THE System SHALL hide the unread count badge on the notifications icon.

---

### Requirement 11: Administrator Dashboard

**User Story:** As an Administrator, I want a dashboard with statistics and management tools, so that I can oversee the entire platform efficiently.

#### Acceptance Criteria

1. WHEN an Administrator accesses the dashboard, THE System SHALL display: the total number of registered Client accounts, the total number of registered Pet records, the count of active Reservations (status Pending or Approved), and the total revenue for the current calendar month calculated as the sum of Total Price of all Reservations with status Completed whose end date falls within the current calendar month.
2. WHEN an Administrator accesses the dashboard, THE System SHALL display the name of the Service with the highest count of Reservations created in the current calendar month. If two or more Services have equal counts, THE System SHALL display the one whose name is first alphabetically.
3. WHEN an Administrator searches or filters Users, the System SHALL support filtering by email address and registration date range. WHEN an Administrator searches or filters Pets, THE System SHALL support filtering by species and owner email. WHEN an Administrator searches or filters Services, THE System SHALL support filtering by availability status. WHEN an Administrator searches or filters Reservations, THE System SHALL support filtering by status and date range.
4. WHEN an Administrator accesses the Contact Messages view, THE System SHALL display all messages submitted via the Contact_Form in reverse chronological order by submission timestamp.
5. IF a non-Administrator user attempts to access any Administrator dashboard view, THEN THE System SHALL return a 403 Forbidden response.

---

### Requirement 12: Client Dashboard

**User Story:** As a Client, I want a personal dashboard, so that I can manage all my pets, reservations, and profile in one place.

#### Acceptance Criteria

1. WHEN an authenticated Client accesses their dashboard, THE System SHALL display the count of Pet records registered under the Client's account and the count of Reservations with status Pending or Approved associated with the Client's account. If either count is zero, THE System SHALL display zero rather than hiding the summary widget.
2. THE System SHALL provide Client-accessible views for managing pets, viewing reservations, updating profile information, and browsing available services.
3. WHEN an authenticated Client accesses their dashboard, THE System SHALL display an unread notification count badge on the notifications icon equal to the number of unread Notifications for that Client. IF the unread count is zero, THE System SHALL hide the badge.
4. IF an authenticated Client attempts to access another Client's pet, reservation, or profile data, THEN THE System SHALL return a 403 Forbidden response.

---

### Requirement 13: Public Website

**User Story:** As a visitor, I want to browse the VIPET public website, so that I can learn about the hotel and its services before registering.

#### Acceptance Criteria

1. THE System SHALL serve a public Home page containing a hero section, VIPET story section, featured services section, "Why Choose VIPET" section, testimonials section, pricing overview section, contact section, and footer.
2. THE System SHALL serve a public About page containing content that covers the hotel's mission and the hotel's story.
3. THE System SHALL serve a public Services page listing all Services marked as available, displaying each service's name, description, and price. IF no Services are marked as available, THE System SHALL display an empty-state message indicating that no services are currently available.
4. THE System SHALL serve a public Pricing page displaying the price of each available Service. IF no Services are available, THE System SHALL display an empty-state message.
5. THE System SHALL serve a public Gallery page displaying images uploaded to the Gallery module. IF no Gallery images exist, THE System SHALL display an empty-state message.
6. THE System SHALL serve a public Contact page containing the Contact_Form.
7. WHEN an unauthenticated visitor navigates to the Login or Register page, THE System SHALL display the respective form. IF an authenticated user navigates to the Login or Register page, THEN THE System SHALL redirect them to their role-appropriate dashboard.
8. THE System SHALL serve all public pages (Home, About, Services, Pricing, Gallery, Contact, Login, Register) without requiring authentication.

---

### Requirement 14: Gallery Module

**User Story:** As a visitor, I want to view a gallery of the hotel's facilities and happy pets, so that I can evaluate the quality of VIPET's services.

#### Acceptance Criteria

1. THE System SHALL display Gallery images on the public Gallery page grouped by the following fixed categories: Suites, Grooming Area, Spa Services, Happy Pets.
2. WHEN an Administrator uploads a Gallery image with a title (1–100 characters), a category selected from the fixed category list, and an image file in JPEG, PNG, or WebP format not exceeding 10 MB, THE System SHALL store it in Media_Storage under the gallery/ subdirectory and make it visible on the public Gallery page.
3. WHEN an Administrator deletes a Gallery image, THE System SHALL remove it from the public Gallery page within 2 seconds of the deletion action being confirmed.
4. IF an Administrator uploads a Gallery image that is not JPEG, PNG, or WebP, or exceeds 10 MB, THEN THE System SHALL reject the upload and display an error message specifying whether the rejection is due to invalid format or size exceeded.

---

### Requirement 15: Contact Module

**User Story:** As a visitor, I want to send a message to VIPET, so that I can ask questions or request information.

#### Acceptance Criteria

1. WHEN a visitor submits the Contact_Form with a name (1–100 characters), a valid email address, a subject (1–150 characters), and a message (1–2000 characters), THE System SHALL store the message in the database and display a success confirmation to the visitor.
2. IF a visitor submits the Contact_Form with any of the following conditions — name missing or empty, email address missing or not in local-part@domain format, subject missing or empty, message missing or empty — THEN THE System SHALL display a field-level validation error for each invalid field, preserve all other submitted field values, and prevent submission.
3. WHEN an Administrator views the Contact Messages section of the dashboard, THE System SHALL display all submitted Contact_Form messages sorted by submission timestamp descending, showing sender name, email, subject, and submission timestamp for each message.
4. IF storing a submitted Contact_Form message fails due to a database error, THEN THE System SHALL display an error message to the visitor and preserve the submitted form data so the visitor can retry.

---

### Requirement 16: Access Control and Security

**User Story:** As a system owner, I want strict role-based access control and secure data handling, so that user data and platform integrity are protected.

#### Acceptance Criteria

1. THE System SHALL enforce authentication on all dashboard, pet management, reservation, and profile endpoints. WHEN an unauthenticated request is made to any of these endpoints, THE System SHALL redirect the request to the login page.
2. THE System SHALL enforce role separation: Clients SHALL NOT access Administrator-only views, and Administrators SHALL NOT access another Client's personal data. IF either access is attempted, THEN THE System SHALL return a 403 Forbidden response.
3. WHEN generating JWT tokens, THE System SHALL set the access token expiry to 60 minutes and the refresh token expiry to 7 days.
4. THE System SHALL use HTTPS for all data transmission in the production environment.
5. THE System SHALL include a valid CSRF token in all HTML forms that use POST, PUT, PATCH, or DELETE HTTP methods, and SHALL reject submissions that do not include a valid CSRF token.
6. IF a request is made to a protected API endpoint without a valid JWT token, THEN THE System SHALL return a 401 Unauthorized response.
7. IF a request is made to a protected HTML endpoint without a valid session, THEN THE System SHALL redirect to the login page.

---

### Requirement 17: Media Storage

**User Story:** As a system owner, I want uploaded files to be stored and served reliably, so that images are always available to users.

#### Acceptance Criteria

1. THE System SHALL store all uploaded media files in the configured Media_Storage directory under the following subdirectories by entity type: pets/ for pet photos, services/ for service images, gallery/ for gallery images, profiles/ for profile photos.
2. THE System SHALL validate the MIME type of every uploaded file against the allowed types (JPEG, PNG, WebP) before storage, rejecting any file whose detected MIME type does not match an allowed type.
3. THE System SHALL validate the size of every uploaded file before storage, applying the following per-entity limits: 5 MB for pet photos, service images, and profile photos; 10 MB for gallery images.
4. IF an uploaded file fails MIME type or size validation, THEN THE System SHALL reject the file, return an error message describing the specific reason for rejection, and SHALL NOT write any part of the file to storage.
5. WHERE Cloudinary credentials (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET) are present in the application settings, THE System SHALL upload media files to Cloudinary instead of local Media_Storage. The upload logic in application code SHALL require no modification to switch between storage backends; only the settings values determine the active backend.

---

### Requirement 18: Technology Stack Compliance

**User Story:** As a developer, I want the application built on the defined technology stack, so that the system is maintainable and consistent.

#### Acceptance Criteria

1. THE System SHALL be implemented using Python 3.11 or higher and Django 5.0 or higher.
2. THE System SHALL use MySQL 8.0 or higher as the relational database engine.
3. THE System SHALL apply Tailwind CSS for all frontend styling using the following brand color values: Primary #FF007F, Dark #1A1A1A, White #FFFFFF, Light Pink #FFE0EF, Gray #666666.
4. THE System SHALL use Bodoni Moda as the typeface for all headings and Jost as the typeface for body text on all rendered pages.
5. IF a user interaction requires client-side JavaScript behavior, THEN THE System SHALL implement that behavior using Alpine.js.
6. WHERE JWT-based API authentication is required, THE System SHALL use the djangorestframework-simplejwt library.
