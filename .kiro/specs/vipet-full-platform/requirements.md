# Requirements Document

## Introduction

VIPET is a luxury pet hotel management platform based in Morocco. The platform enables pet owners (clients) to register their pets, browse premium services (Luxury Suite, Grooming, Spa, Daycare, Training, Veterinary Checkup, Birthday Events), make reservations, and receive notifications on reservation status changes. Administrators manage services, reservations, users, gallery content, and contact submissions. The system is built on Django 5.x with Django REST Framework, JWT authentication, Tailwind CSS + Alpine.js frontend, and supports both MySQL (production) and SQLite (development).

## Glossary

- **Platform**: The VIPET luxury pet hotel web application
- **Client**: A registered user with the "client" role who owns pets and makes reservations
- **Administrator**: A registered user with the "admin" role who manages the platform
- **CustomUser**: The Django user model using email-based authentication with role field (client/admin)
- **Pet**: An animal registered by a Client, with species, breed, gender, age, weight, medical notes, and vaccination status
- **Service**: A luxury pet hotel offering categorized into one of seven types, priced in MAD (Moroccan Dirham)
- **Reservation**: A booking linking a Pet to a Service with start/end dates and a status workflow
- **Notification**: An auto-generated message informing a Client of reservation status changes
- **Gallery_Image**: A photo uploaded by an Administrator for public display
- **Contact_Message**: A public form submission from a visitor or client, stored for admin review
- **JWT_Token**: A JSON Web Token (access or refresh) used for stateless API authentication
- **Image_Validator**: The server-side component that checks uploaded file MIME types and sizes via libmagic
- **MAD**: Moroccan Dirham, the currency used for service pricing
- **KPI**: Key Performance Indicator displayed on the administrator dashboard
- **DRF**: Django REST Framework, the API toolkit used for serialization and viewsets
- **Rate_Limiter**: The cache-based mechanism that tracks failed login attempts per IP address

## Requirements

### Requirement 1: User Registration

**User Story:** As a visitor, I want to register an account with my email address, so that I can access the platform as a client.

#### Acceptance Criteria

1. WHEN a visitor submits a valid registration form with email (max 254 characters), first name (max 50 characters), last name (max 50 characters), password (8–128 characters), password confirmation, and optional phone number (max 20 characters), THE Platform SHALL create a new CustomUser with the "client" role, a hashed password, and is_active set to true, and then redirect the visitor to the login page
2. WHEN a visitor submits a registration form with an email that already exists in the system, THE Platform SHALL display a validation error indicating the email is already registered, without creating a duplicate account
3. WHEN a visitor submits a registration form with an invalid email format, THE Platform SHALL reject the submission and display a field-level validation error on the email field
4. WHEN a visitor submits a registration form where the password and password confirmation fields do not match, THE Platform SHALL display a validation error on the confirmation field indicating the mismatch
5. IF a visitor submits a registration form with a password that fails Django password validation (MinimumLengthValidator, CommonPasswordValidator, NumericPasswordValidator, or UserAttributeSimilarityValidator), THEN THE Platform SHALL display each specific validation failure message returned by the failing validators
6. WHILE a user is already authenticated, THE Platform SHALL redirect any request to the registration page to the client dashboard (for client role) or the admin panel (for admin role)
7. WHEN a visitor submits a registration form with first name or last name left empty, THE Platform SHALL reject the submission and display a required-field validation error on the corresponding field

### Requirement 2: User Login and Session Management

**User Story:** As a registered user, I want to log in with my email and password, so that I can access my role-specific dashboard.

#### Acceptance Criteria

1. WHEN a user submits valid email and password credentials for an active account, THE Platform SHALL authenticate the user, create a session, and redirect to the role-appropriate dashboard within 3 seconds of form submission
2. WHEN a user with role "admin" logs in successfully, THE Platform SHALL redirect to the administrator dashboard at /admin-panel/
3. WHEN a user with role "client" logs in successfully, THE Platform SHALL redirect to the client dashboard at /client/
4. WHEN a user submits credentials that do not match any active account, THE Platform SHALL display a non-field error message "Invalid email address or password." without revealing whether the email exists or the password is incorrect
5. WHEN more than 5 failed login attempts occur from the same IP address within a 900-second (15-minute) window, THE Rate_Limiter SHALL block further authentication attempts and display a non-field error message indicating too many failed attempts and to retry after 15 minutes
6. WHEN a blocked IP address's failure counter expires after 900 seconds of no additional failed attempts, THE Rate_Limiter SHALL allow authentication attempts from that IP address again
7. WHEN a user logs in successfully after previous failures, THE Rate_Limiter SHALL delete the failure counter for that IP address
8. WHILE a user is already authenticated, THE Platform SHALL redirect any request to the login page to the user's role-appropriate dashboard (admin to /admin-panel/, client to /client/)
9. IF a user submits the login form with an empty email or empty password field, THEN THE Platform SHALL re-display the login form with a validation error indicating the missing field, without making an authentication attempt

### Requirement 3: User Logout

**User Story:** As an authenticated user, I want to log out, so that my session is terminated securely.

#### Acceptance Criteria

1. WHEN an authenticated user requests logout, THE Platform SHALL invalidate the server-side session and redirect the user to the site root ("/")
2. THE Platform SHALL accept logout requests via both POST and GET HTTP methods
3. WHEN an authenticated user has logged out, THE Platform SHALL deny access to any session-protected resource until the user authenticates again
4. IF an unauthenticated user requests logout, THEN THE Platform SHALL redirect to the site root ("/") without displaying an error

### Requirement 4: JWT API Authentication

**User Story:** As a developer integrating with the API, I want to obtain and refresh JWT tokens, so that I can make authenticated API requests without session state.

#### Acceptance Criteria

1. WHEN a registered email and correct password are submitted to /api/v1/token/, THE Platform SHALL return a JSON response containing an "access" token valid for 60 minutes and a "refresh" token valid for 7 days
2. WHEN a valid, non-expired refresh token is submitted to /api/v1/token/refresh/, THE Platform SHALL return a JSON response containing a new "access" token valid for 60 minutes without rotating the refresh token
3. WHEN a non-expired, platform-issued token is submitted to /api/v1/token/verify/, THE Platform SHALL return a 200 status
4. IF an expired or unrecognized token is submitted to /api/v1/token/verify/, THEN THE Platform SHALL return a 401 status
5. WHEN an API request includes a valid, non-expired Bearer token in the Authorization header, THE Platform SHALL process the request as the user identified by the token's user_id claim
6. WHEN an API request includes an expired or invalid Bearer token in the Authorization header, THE Platform SHALL return a 401 Unauthorized response with a JSON body containing an error message indicating the token is invalid or expired
7. IF an unregistered email, incorrect password, or missing credentials are submitted to /api/v1/token/, THEN THE Platform SHALL return a 401 Unauthorized response with a JSON body containing an error message indicating invalid credentials
8. IF an expired or invalid refresh token is submitted to /api/v1/token/refresh/, THEN THE Platform SHALL return a 401 Unauthorized response with a JSON body containing an error message indicating the token is invalid or expired

### Requirement 5: Password Reset

**User Story:** As a user who forgot my password, I want to request a password reset via email, so that I can regain access to my account.

#### Acceptance Criteria

1. WHEN a user submits a password reset request for any email address, THE Platform SHALL display the same confirmation message regardless of whether the email is registered (anti-enumeration)
2. WHEN a user submits a password reset request for a registered active email, THE Platform SHALL send an email containing a unique reset link with a URL-safe base64-encoded UID and a one-time token
3. WHEN a user follows a valid reset link within 60 minutes, THE Platform SHALL display a form requiring a new password (8 to 128 characters) and a matching confirmation field
4. IF a user follows a reset link after 60 minutes or with an invalid/tampered UID or token, THEN THE Platform SHALL display an error message indicating the link is expired or invalid, along with a link to request a new reset
5. WHEN a user submits a new password via the reset form where both password fields match and the password passes Django password validators (minimum 8 characters, not a common password, not entirely numeric, not too similar to user attributes), THE Platform SHALL update the password hash, invalidate the used token, and redirect the user to the login page
6. IF a user submits a new password via the reset form where the two password fields do not match or the password fails validation, THEN THE Platform SHALL re-display the form with an error message indicating the specific validation failure
7. THE Platform SHALL validate the new password against Django password validators (minimum 8 characters, not a common password, not entirely numeric, not too similar to user attributes)

### Requirement 6: User Profile Management

**User Story:** As an authenticated user, I want to view and update my profile information, so that I can keep my personal details current.

#### Acceptance Criteria

1. WHEN an authenticated user visits the profile page, THE Platform SHALL display a form pre-populated with the user's current first name (max 50 characters), last name (max 50 characters), phone number (max 20 characters, optional), and profile photo
2. WHEN an authenticated user visits the profile page, THE Platform SHALL display the user's email address as read-only text that is not editable via the form
3. WHEN an authenticated user submits the profile update form with a first name and last name each between 1 and 50 characters, and an optional phone number of up to 20 characters, THE Platform SHALL save the changes and display a success message within 2 seconds
4. IF an authenticated user submits the profile update form with a missing first name, missing last name, or any field exceeding its maximum length, THEN THE Platform SHALL reject the submission, preserve the entered form data, and display a validation error message identifying each invalid field
5. WHEN an authenticated user uploads a profile photo, THE Image_Validator SHALL verify the file MIME type (detected via file content inspection, not file extension) is JPEG, PNG, or WebP and the file size does not exceed 5 MB
6. IF an uploaded profile photo fails MIME type or size validation, THEN THE Platform SHALL reject the upload and display an error message indicating whether the file type is unsupported or the size limit was exceeded
7. WHILE no profile photo has been uploaded, THE Platform SHALL display a default SVG avatar placeholder
8. IF an unauthenticated user attempts to access the profile page, THEN THE Platform SHALL redirect the user to the login page

### Requirement 7: Pet Management

**User Story:** As a client, I want to manage my pet profiles, so that I can make reservations for specific pets.

#### Acceptance Criteria

1. WHEN a client submits a valid pet creation form, THE Platform SHALL create a Pet record associated with the authenticated client, including name (maximum 100 characters), species, breed (maximum 100 characters, optional), gender (male, female, or unknown), date of birth, weight in kilograms, medical notes (optional), vaccination status (up_to_date, overdue, or unknown), and optional photo
2. WHEN a client views the pet list, THE Platform SHALL display only pets owned by that client
3. WHEN a client submits a valid pet update form, THE Platform SHALL update the specified Pet record only if the client owns that pet
4. WHEN a client requests deletion of a pet, THE Platform SHALL remove the Pet record only if the client owns that pet and the pet has no associated future reservations
5. IF a client attempts to access or modify a pet owned by another client, THEN THE Platform SHALL deny the request with an error indicating insufficient permissions
6. WHEN a client uploads a pet photo, THE Image_Validator SHALL verify the file MIME type is JPEG, PNG, or WebP and the size does not exceed 5 MB
7. THE Platform SHALL validate that pet weight is a positive decimal value between 0.01 and 999.99 kilograms with a maximum of 2 decimal places
8. IF a client submits a pet date of birth that is in the future, THEN THE Platform SHALL reject the submission with an error message indicating the date of birth must not be in the future
9. THE Platform SHALL provide species choices including at minimum: Dog, Cat, Bird, Rabbit, and Other
10. IF a client submits a pet creation or update form with any required field missing or empty, THEN THE Platform SHALL reject the submission with an error message indicating which fields are required
11. IF a client requests deletion of a pet that has associated future reservations, THEN THE Platform SHALL reject the deletion with an error message indicating the pet cannot be removed while future reservations exist

### Requirement 8: Service Management

**User Story:** As an administrator, I want to manage services offered by the hotel, so that clients can browse and book available services.

#### Acceptance Criteria

1. WHEN an administrator submits a service creation form with a valid name (1–100 characters), a valid category, a description (1–1000 characters), a price between 0.01 and 999999.99 MAD, and an optional image, THE Platform SHALL create a Service record with those fields and is_available defaulting to true
2. WHEN an administrator submits a service update form with valid field values for an existing service, THE Platform SHALL update the specified Service record and set the updated_at timestamp
3. WHEN an administrator requests deletion of an existing service, THE Platform SHALL permanently remove the Service record from the system
4. THE Platform SHALL validate that service price is a positive decimal value between 0.01 and 999999.99 MAD with at most 2 decimal places
5. THE Platform SHALL enforce that the service category is one of: Luxury Suite, Grooming, Spa, Daycare, Training, Veterinary Checkup, Birthday Events
6. IF a non-administrator user attempts to create, update, or delete a service, THEN THE Platform SHALL reject the request with a 403 Forbidden response and leave the service data unchanged
7. WHEN an administrator toggles the availability status of a service, THE Platform SHALL update the is_available field to the opposite boolean value
8. IF an administrator submits a service creation or update form with invalid or missing required fields, THEN THE Platform SHALL reject the submission and return a validation error message indicating each field that failed validation
9. IF an administrator requests deletion or update of a service that does not exist, THEN THE Platform SHALL return a not-found error response without modifying any data

### Requirement 9: Service Browsing

**User Story:** As a visitor or client, I want to browse available services, so that I can learn about offerings and make informed booking decisions.

#### Acceptance Criteria

1. THE Platform SHALL display the services listing page to both authenticated and unauthenticated users without requiring login
2. WHEN a user views the services page without filters, THE Platform SHALL display all services where is_available is True, ordered alphabetically by name in ascending order
3. WHEN a user filters services by category, THE Platform SHALL display only services where is_available is True and category matches one of the 7 valid categories: luxury_suite, grooming, spa, daycare, training, veterinary_checkup, or birthday_events
4. THE Platform SHALL display for each service: name (up to 100 characters), category label (human-readable display name), description (up to 1000 characters), price in MAD formatted to 2 decimal places (range 0.01 to 999,999.99), and image if present or no image placeholder if absent
5. THE Platform SHALL provide a REST API endpoint for service listing that accepts optional query parameters for filtering by category and by availability, and returns only services where is_available is True by default
6. IF a user filters by category and no services match the selected category, THEN THE Platform SHALL display an empty list with no error
7. IF the API receives an invalid category value not in the 7 defined categories, THEN THE Platform SHALL return an empty results set

### Requirement 10: Reservation Creation

**User Story:** As a client, I want to create a reservation for my pet, so that I can book a hotel service for a specific date range.

#### Acceptance Criteria

1. WHEN a client submits a valid reservation form with a pet, service, start date, end date, and optional notes (maximum 500 characters), THE Platform SHALL create a Reservation record with status "Pending" and timestamps for created_at and updated_at
2. THE Platform SHALL validate that the selected pet belongs to the authenticated client
3. THE Platform SHALL validate that the selected service has is_available set to True
4. THE Platform SHALL validate that the start date is equal to or later than the current server date
5. THE Platform SHALL validate that the end date is at least one day after the start date
6. IF any reservation validation fails, THEN THE Platform SHALL reject the submission with descriptive error messages identifying each violation and preserve the submitted form data so the client can correct and resubmit
7. WHEN a reservation is successfully created, THE Platform SHALL generate a Notification for the client confirming the pending reservation, including the pet name, service name, and selected dates
8. IF a non-authenticated user or a user with role "admin" attempts to create a reservation, THEN THE Platform SHALL return a 403 Forbidden response
9. IF the notes field exceeds 500 characters, THEN THE Platform SHALL reject the submission with an error message indicating the maximum allowed length

### Requirement 11: Reservation Status Workflow

**User Story:** As an administrator, I want to manage reservation statuses, so that I can approve, reject, or mark reservations as completed.

#### Acceptance Criteria

1. WHEN an administrator approves a reservation with status "Pending", THE Platform SHALL update the status to "Approved" and record the timestamp of the transition
2. WHEN an administrator rejects a reservation with status "Pending", THE Platform SHALL update the status to "Rejected" and record the timestamp of the transition
3. WHEN an administrator completes a reservation with status "Approved", THE Platform SHALL update the status to "Completed" and record the timestamp of the transition
4. IF an administrator or client attempts a status transition not in the allowed workflow (Pending→Approved, Pending→Rejected, Pending→Cancelled, Approved→Completed), THEN THE Platform SHALL reject the transition and display an error message indicating the current status and the reason the transition is not allowed
5. WHEN a reservation status changes, THE Platform SHALL generate a Notification for the owning client that includes the reservation identifier, the previous status, and the new status within 5 seconds of the transition
6. WHEN a client cancels their own reservation with status "Pending", THE Platform SHALL update the status to "Cancelled" and record the timestamp of the transition
7. IF a client attempts to cancel a reservation that is not in "Pending" status, THEN THE Platform SHALL reject the cancellation and display an error message indicating the current status and the reason the cancellation is not allowed
8. IF a client attempts to cancel a reservation that they do not own, THEN THE Platform SHALL reject the request and display an error message indicating the operation is not permitted

### Requirement 12: Reservation Viewing

**User Story:** As a user, I want to view reservations relevant to my role, so that I can track bookings.

#### Acceptance Criteria

1. WHEN a client views the reservations list, THE Platform SHALL display only reservations belonging to that client
2. WHEN an administrator views the reservations list, THE Platform SHALL display all reservations across all clients
3. IF a client attempts to access reservation details belonging to another client via the API, THEN THE Platform SHALL return a 403 Forbidden response
4. THE Platform SHALL support filtering reservations by status (Pending, Approved, Rejected, Completed, Cancelled), where omitting the status filter returns all reservations visible to the user's role
5. THE Platform SHALL paginate reservation lists with a default page size of 10 items per page
6. WHEN a paginated reservation list is returned via the API, THE Platform SHALL include pagination metadata: total count, next page URL, and previous page URL (or null if not applicable)
7. THE Platform SHALL display for each reservation: pet name, service name, start date, end date, status, and creation date
8. THE Platform SHALL order reservations by creation date descending (most recent first)
9. WHEN the reservations list contains no results matching the current filters, THE Platform SHALL display an empty list with zero items and no error

### Requirement 13: Notifications

**User Story:** As a client, I want to receive notifications when my reservation status changes, so that I stay informed about my bookings.

#### Acceptance Criteria

1. WHEN a reservation status changes, THE Platform SHALL create a Notification record linked to the reservation's owning client containing a message that includes the pet name, service name, and the new status value (Approved, Rejected, Completed, or Cancelled)
2. WHEN a client views notifications, THE Platform SHALL display only notifications belonging to that client ordered by creation date descending, returning a maximum of 50 notifications per page
3. WHEN a client marks a notification as read, THE Platform SHALL update the is_read field to True. IF the notification is already marked as read, THEN THE Platform SHALL leave the is_read field unchanged and return a success response
4. THE Platform SHALL provide an API endpoint returning the count of unread notifications for the authenticated client as an integer value (0 when no unread notifications exist)
5. THE Platform SHALL provide a REST API under the api_notifications namespace at /api/v1/notifications/ supporting listing notifications with pagination and marking individual notifications as read
6. IF a client attempts to access or modify a notification belonging to another client, THEN THE Platform SHALL return a 403 Forbidden response
7. IF a client attempts to mark a notification as read using a notification identifier that does not exist, THEN THE Platform SHALL return a 404 Not Found response

### Requirement 14: Administrator Dashboard

**User Story:** As an administrator, I want a dashboard showing key metrics and management interfaces, so that I can monitor and control the platform.

#### Acceptance Criteria

1. WHEN an administrator accesses the dashboard, THE Platform SHALL display these KPIs: total registered users, total registered pets, count of active reservations (status Pending or Approved), monthly revenue from completed reservations in MAD (summing service prices of reservations with status "Completed" whose end date falls within the current calendar month), and the most requested service name (the service with the highest total reservation count across all time, with alphabetical order as tiebreaker)
2. WHEN an administrator views the user management section, THE Platform SHALL display a paginated list (20 items per page) of all users sorted by date joined descending, showing email, full name, role, and date joined
3. WHEN an administrator views the pet management section, THE Platform SHALL display a paginated list (20 items per page) of all pets sorted by creation date descending, showing name, species, owner email, and creation date
4. WHEN an administrator views the reservation management section, THE Platform SHALL display a paginated list (20 items per page) of all reservations sorted by creation date descending, showing client email, pet name, service name, start date, end date, and status, with action buttons for valid status transitions
5. IF a non-administrator user attempts to access the administrator dashboard, THEN THE Platform SHALL return a 403 Forbidden response
6. IF no reservations with status "Completed" exist for the current calendar month, THEN THE Platform SHALL display 0.00 MAD as the monthly revenue
7. IF no reservations exist in the system, THEN THE Platform SHALL display "N/A" as the most requested service name
8. IF an unauthenticated user attempts to access the administrator dashboard, THEN THE Platform SHALL redirect the user to the login page

### Requirement 15: Client Dashboard

**User Story:** As a client, I want a personal dashboard showing my pets and recent activity, so that I can quickly navigate to key areas.

#### Acceptance Criteria

1. WHEN an authenticated client accesses the dashboard, THE Platform SHALL display the count of the client's own registered pets and a list of the client's 5 most recent reservations ordered by creation date descending
2. THE Platform SHALL provide navigation links from the client dashboard to: pet management, reservation creation, reservation history, notifications, and profile
3. IF a non-authenticated user attempts to access the client dashboard, THEN THE Platform SHALL redirect to the login page
4. IF an authenticated user with the admin role attempts to access the client dashboard, THEN THE Platform SHALL return an HTTP 403 Forbidden response
5. IF the authenticated client has zero registered pets or zero reservations, THEN THE Platform SHALL display the dashboard with a count of 0 for pets and an empty reservations list respectively

### Requirement 16: Gallery Module

**User Story:** As a visitor or client, I want to view a gallery of the hotel, and as an administrator, I want to manage gallery images, so that the platform showcases the facility.

#### Acceptance Criteria

1. THE Platform SHALL display the gallery page at /gallery/ with a responsive grid layout showing only Gallery_Image records where is_published is True, ordered by upload date descending (newest first), to both authenticated and unauthenticated users
2. WHEN an administrator uploads a gallery image with a title (maximum 100 characters) and an optional description (maximum 500 characters), THE Platform SHALL create a Gallery_Image record after passing image validation
3. WHEN an administrator requests deletion of a gallery image, THE Platform SHALL remove the Gallery_Image record and the associated file from storage
4. IF a non-administrator user attempts to upload or delete gallery images, THEN THE Platform SHALL return a 403 Forbidden response
5. WHEN an administrator uploads a gallery image, THE Image_Validator SHALL verify the file MIME type is JPEG, PNG, or WebP and the file size does not exceed 5 MB
6. IF image validation fails during upload, THEN THE Platform SHALL reject the upload, preserve no Gallery_Image record, and return an error message indicating the validation failure reason (invalid format or size exceeded)
7. IF an administrator submits a gallery image upload with a title exceeding 100 characters, a missing title, or a description exceeding 500 characters, THEN THE Platform SHALL reject the upload and return an error message indicating which field constraint was violated

### Requirement 17: Contact Form

**User Story:** As a visitor or client, I want to submit a contact message, and as an administrator, I want to review those messages, so that communication between visitors and the hotel is facilitated.

#### Acceptance Criteria

1. THE Platform SHALL display the contact form with name, email, subject, and message body fields to both authenticated and unauthenticated users
2. WHEN a visitor submits a valid contact form with name, email, subject, and message body, THE Platform SHALL create a Contact_Message record with is_read set to False and display a success confirmation message to the visitor
3. WHEN an administrator views the contact inbox, THE Platform SHALL display all messages ordered by submission date descending with read/unread status indication
4. WHEN an administrator opens a contact message, THE Platform SHALL mark the message as read by setting is_read to True
5. IF a non-administrator user attempts to access the contact inbox, THEN THE Platform SHALL return a 403 Forbidden response
6. THE Platform SHALL validate that the contact form email field conforms to standard email format (local-part@domain with valid domain structure)
7. THE Platform SHALL validate that name is non-empty and at most 100 characters, subject is non-empty and at most 200 characters, and message body is non-empty and at most 2000 characters
8. IF a visitor submits the contact form with any validation error (missing required field, email format invalid, or field exceeding maximum length), THEN THE Platform SHALL reject the submission, preserve the entered form data, and display an error message indicating which field(s) failed validation

### Requirement 18: Public Website Pages

**User Story:** As a visitor, I want to browse public pages of the website, so that I can learn about VIPET's offerings before registering.

#### Acceptance Criteria

1. THE Platform SHALL serve a public home page at the root URL (/) that displays a minimum of 3 and a maximum of 6 featured services and includes a visible call-to-action link or button navigating to the registration page
2. THE Platform SHALL serve a public about page at /about/ describing the hotel's mission and luxury positioning
3. THE Platform SHALL serve a public services page at /services/ displaying available services (as defined in Requirement 9)
4. THE Platform SHALL serve a public gallery page at /gallery/ displaying hotel images (as defined in Requirement 16)
5. THE Platform SHALL serve a public contact page at /contact/ with the contact form (as defined in Requirement 17)
6. THE Platform SHALL render all public pages with responsive design using Tailwind CSS, adapting layout for viewports at the sm (640px), md (768px), and lg (1024px) breakpoints
7. THE Platform SHALL serve all public pages (/, /about/, /services/, /gallery/, /contact/) without requiring user authentication, returning HTTP 200 for unauthenticated requests
8. WHEN a visitor requests a public page, THE Platform SHALL return the fully rendered HTML response within 3 seconds under normal load

### Requirement 19: Error Handling Pages

**User Story:** As a user, I want to see informative error pages when something goes wrong, so that I understand the issue and can navigate back to working pages.

#### Acceptance Criteria

1. WHEN a user accesses a resource they are not authorized to view, THE Platform SHALL return an HTTP 403 status code and render a custom error page that displays the error code "403", a heading indicating access is forbidden, a message explaining the user does not have permission, and a "Go Home" link pointing to the site root URL
2. WHEN a user accesses a URL that does not match any registered route, THE Platform SHALL return an HTTP 404 status code and render a custom error page that displays the error code "404", a heading indicating the page was not found, a message explaining the page does not exist, and a "Go Home" link pointing to the site root URL
3. WHEN an unhandled server error occurs, THE Platform SHALL return an HTTP 500 status code and render a custom error page that displays the error code "500", a heading indicating a server error, a message explaining something went wrong, and a "Go Home" link pointing to the site root URL
4. THE Platform SHALL register custom error handler functions for HTTP status codes 403, 404, and 500 in the root URL configuration
5. THE Platform SHALL render each error page as a self-contained HTML document with inline styles, so that the page displays correctly even when external stylesheets or database connections are unavailable

### Requirement 20: Image Upload Validation

**User Story:** As the platform, I want to validate all uploaded images by inspecting MIME type and file size, so that only safe and appropriately-sized images are stored.

#### Acceptance Criteria

1. WHEN a file is uploaded, THE Image_Validator SHALL read the first 2048 bytes and detect the MIME type using libmagic rather than trusting the file extension
2. IF the detected MIME type is not one of image/jpeg, image/png, or image/webp, THEN THE Image_Validator SHALL reject the file with an error message identifying the detected type
3. IF the file size exceeds the configured maximum (5 MB by default), THEN THE Image_Validator SHALL reject the file with an error message showing the actual size in megabytes and the configured limit in megabytes
4. WHEN the Image_Validator reads file bytes for MIME detection, THE Image_Validator SHALL reset the file pointer to position 0 after reading so that subsequent file operations proceed correctly
5. WHEN a file passes both MIME type and size validation, THE Image_Validator SHALL leave the file content unmodified such that reading the entire file after validation yields byte-for-byte identical content to the original upload
6. WHEN a file is uploaded, THE Image_Validator SHALL check the MIME type before checking the file size, so that a file failing both checks is rejected with the MIME type error
7. IF the uploaded file contains 0 bytes, THEN THE Image_Validator SHALL reject the file with an error message identifying the detected type as invalid

### Requirement 21: API Serialization and Filtering

**User Story:** As a developer consuming the API, I want consistent serialization, pagination, and filtering across endpoints, so that API integration is predictable.

#### Acceptance Criteria

1. THE Platform SHALL use Django REST Framework serializers for all API responses, returning JSON objects where each field name matches the corresponding model field name
2. THE Platform SHALL apply DjangoFilterBackend as the default filter backend for all API viewsets
3. THE Platform SHALL support pagination on all list API endpoints with a default page size of 20 and a maximum configurable page size of 100
4. WHEN an API list request includes filter query parameters, THE Platform SHALL return only resources matching the filter criteria
5. IF an API list request includes an unrecognized filter query parameter, THEN THE Platform SHALL ignore the unrecognized parameter and return results as if it were not provided
6. THE Platform SHALL serialize decimal price fields as strings with exactly two decimal places (e.g., "29.99", "100.00") to avoid floating-point precision issues
7. THE Platform SHALL include all foreign key identifiers present on the model in serialized API responses
8. THE Platform SHALL ensure that for any model instance, serializing and then deserializing the resource produces field values equivalent to the original instance (round-trip consistency)
