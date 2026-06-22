# Requirements Document

## Introduction

This document defines the requirements for the VIPet Premium Services feature of the VIPET luxury pet hotel platform. Premium Services extends the core platform with high-value add-on services that enhance the client experience during their pet's stay. These services include luxury van transport with real-time GPS tracking, birthday and anniversary party events with customizable themes and packages, live camera streaming for remote pet monitoring, and daily photo/video updates from staff. All premium services are linked to active reservations and integrate with the existing cart, payment, notification, and reservation systems.

## Glossary

- **Premium_Service**: A high-value add-on service bookable by clients in addition to core boarding and care services, linked to an active Reservation
- **Transport_Booking**: A scheduled van pickup and/or delivery request for a pet, linking a Reservation to a Van with address, time, and status tracking
- **Van**: A VIPet-branded vehicle equipped with a GPS tracking device, used for pet transport with a defined passenger capacity
- **GPS_Location**: A recorded geographic position (latitude, longitude) of a Van at a specific point in time during an active transport
- **GPS_Polling_Service**: A background process that periodically queries the GPS device API to retrieve and store Van location data
- **Event_Booking**: A birthday or anniversary party request for a pet, linked to a Reservation with a selected theme, tier, and optional add-ons
- **Event_Theme**: A named party style (princess, superhero, garden party, etc.) available for selection when booking an event
- **Event_Tier**: A service package level (basic, premium, VIP) defining included features and base price for an event
- **Event_Add_On**: An optional extra item (custom cake, extra decorations, photo package, video package, extra pet guest) purchasable alongside an Event_Booking
- **Camera**: An IP-based video camera installed in a suite, play area, pool, or garden that captures a live RTSP/HLS video feed
- **Stream_Access**: A time-limited, token-authenticated permission granting a Client access to view a specific Camera feed linked to their Reservation
- **Media_Update**: A photo or video file uploaded by staff during a pet's stay, linked to a Reservation and Pet, with optional caption and auto-generated thumbnail
- **Client**: An authenticated user with role "client" who books services for their pets
- **Staff**: An authenticated user with is_staff=True or role "admin" who manages operations at VIPet
- **Reservation**: An existing booking linking a Pet to a Service with start/end dates and a status workflow (pending, approved, rejected, completed, cancelled)
- **HLS_Stream**: An HTTP Live Streaming URL providing browser-compatible video playback from a Camera
- **Access_Token**: A cryptographic string used to authenticate a Client's access to an HLS_Stream

## Requirements

### Requirement 1: Transport Booking Creation

**User Story:** As a client, I want to book a van to pick up and/or deliver my pet to VIPet, so that my pet travels safely and comfortably without me needing to arrange my own transport.

#### Acceptance Criteria

1. WHEN a Client submits a transport booking request with a valid Reservation, Pet, direction (pickup, delivery, or both), pickup address, and scheduled datetime, THE Transport_Booking SHALL be created with status "scheduled" and linked to the specified Reservation
2. WHEN a Client selects direction "both", THE Transport_Booking SHALL create a logical round-trip record covering both pickup (home to VIPet) and delivery (VIPet to home)
3. THE Transport_Booking SHALL validate that the scheduled datetime is in the future and falls within the associated Reservation date range
4. THE Transport_Booking SHALL validate that the specified Pet belongs to the authenticated Client and is linked to the specified Reservation
5. THE Transport_Booking SHALL validate that the Reservation has status "approved" before allowing booking creation
6. THE Transport_Booking SHALL require a non-empty pickup address with a maximum length of 500 characters
7. IF a Client submits a transport booking request with an invalid or past scheduled datetime, THEN THE System SHALL reject the request and return an error message identifying the invalid field
8. IF a Client submits a transport booking request for a Reservation that does not belong to them, THEN THE System SHALL reject the request with a 403 Forbidden response
9. WHEN a Transport_Booking is successfully created, THE System SHALL send a Notification to the Client confirming the booking with the scheduled date, time, and direction

### Requirement 2: Transport Status Lifecycle

**User Story:** As a client, I want to receive updates as my pet's transport progresses through each stage, so that I know exactly where my pet is in the process.

#### Acceptance Criteria

1. THE Transport_Booking SHALL enforce the following status transitions: scheduled → en_route_pickup, en_route_pickup → pet_collected, pet_collected → en_route_delivery, en_route_delivery → completed; and cancellation is permitted from scheduled, en_route_pickup states only
2. WHEN a Staff member advances a Transport_Booking status, THE System SHALL validate that the transition is permitted by the state machine before applying the change
3. WHEN a Transport_Booking status changes to "en_route_pickup" or "en_route_delivery", THE GPS_Polling_Service SHALL activate location tracking for the assigned Van
4. WHEN a Transport_Booking status changes to "completed" or "cancelled", THE GPS_Polling_Service SHALL deactivate location tracking for the assigned Van
5. WHEN a Transport_Booking status changes, THE System SHALL send a Notification to the Client describing the new status
6. IF a Client attempts to cancel a Transport_Booking that is in status "pet_collected" or later, THEN THE System SHALL reject the cancellation and return an error message indicating the transport is already in progress
7. THE Transport_Booking SHALL only allow Staff members to advance the status forward (except cancellation, which a Client may also initiate from eligible states)

### Requirement 3: GPS Real-Time Tracking

**User Story:** As a client, I want to see my pet's transport van location in real time on a map, so that I can track the van's progress during pickup or delivery.

#### Acceptance Criteria

1. WHILE a Transport_Booking has status "en_route_pickup" or "en_route_delivery", THE GPS_Polling_Service SHALL poll the GPS device API every 10 seconds and store each GPS_Location record with latitude, longitude, speed, heading, and timestamp
2. WHEN a Client requests the current location for an active Transport_Booking, THE System SHALL return the most recent GPS_Location record for that booking
3. WHEN a Client requests route history for a Transport_Booking, THE System SHALL return all GPS_Location records for that booking ordered by recorded timestamp ascending
4. THE GPS_Location SHALL validate that latitude is between -90 and 90, longitude is between -180 and 180, and recorded timestamp is not in the future
5. THE System SHALL only allow a Client to access GPS tracking data for Transport_Bookings belonging to that Client
6. IF the GPS device API is unreachable during a polling cycle, THEN THE GPS_Polling_Service SHALL log the failure, skip that cycle, and retry on the next scheduled interval without interrupting the tracking session
7. WHEN a Transport_Booking status transitions out of an active tracking state, THE GPS_Polling_Service SHALL stop polling within 10 seconds of the status change

### Requirement 4: Van Management

**User Story:** As an admin, I want to manage the fleet of VIPet transport vans, so that I can assign available vans to transport bookings.

#### Acceptance Criteria

1. THE Admin SHALL be able to create a Van with: registration plate (unique, maximum 20 characters), name (maximum 50 characters), capacity (positive integer, minimum 1), GPS device ID (unique, maximum 100 characters), active status, and optional image
2. THE Admin SHALL be able to assign a Van to a Transport_Booking by updating the booking with the selected Van and driver name
3. WHEN a Van is assigned to a Transport_Booking, THE System SHALL validate that the Van is_active is True and that the Van is not already assigned to another Transport_Booking with an active transport status (en_route_pickup, pet_collected, or en_route_delivery) at the same scheduled time
4. THE Admin SHALL be able to deactivate a Van by setting is_active to False, which prevents future assignment but does not affect in-progress transports
5. IF the Admin attempts to create a Van with a duplicate registration plate or GPS device ID, THEN THE System SHALL reject the creation and return an error message identifying the duplicate field

### Requirement 5: Event Booking Creation

**User Story:** As a client, I want to book a birthday or anniversary party for my pet during their stay, so that my pet can celebrate a special occasion at VIPet.

#### Acceptance Criteria

1. WHEN a Client submits an event booking request with a valid Reservation, Pet, Event_Theme, Event_Tier, event date, event time, and optional add-ons, THE Event_Booking SHALL be created with status "pending" and a calculated total price
2. THE Event_Booking SHALL validate that the event date falls within the associated Reservation start_date and end_date (inclusive)
3. THE Event_Booking SHALL validate that the event time is within operating hours (08:00 to 20:00 inclusive)
4. THE Event_Booking SHALL validate that the Pet does not already have a confirmed Event_Booking on the same event date
5. THE Event_Booking SHALL validate that the specified Reservation has status "approved"
6. THE Event_Booking SHALL validate that the selected Event_Theme has is_available set to True
7. THE Event_Booking total_price SHALL equal the Event_Tier base_price plus the sum of all selected Event_Add_On prices, rounded to 2 decimal places
8. WHEN an Event_Booking is successfully created, THE System SHALL send a Notification to the Client confirming the event request with theme, date, and total price
9. IF any validation fails during event booking creation, THEN THE System SHALL reject the request and return error messages identifying each invalid field

### Requirement 6: Event Themes and Tiers Management

**User Story:** As an admin, I want to manage event themes, tier packages, and add-on pricing, so that I can customize the party offerings for clients.

#### Acceptance Criteria

1. THE Admin SHALL be able to create and update an Event_Theme with: name (maximum 100 characters), description (maximum 500 characters), optional image, and availability status
2. THE Admin SHALL be able to create and update an Event_Tier with: name (basic, premium, or VIP), description (maximum 500 characters), base_price in MAD (positive, maximum 99,999.99), and boolean flags for cake, decorations, photo package, video package inclusions, and maximum pet guests (positive integer)
3. THE System SHALL provide three predefined Event_Tier levels: basic, premium, and VIP, each with distinct base prices and inclusion sets
4. THE Admin SHALL be able to define Event_Add_On types with configurable prices in MAD, where each add-on has a type (cake, decorations, photo, video, extra_guest), optional description (maximum 200 characters), and price (positive, maximum 9,999.99 MAD)
5. WHEN an Event_Theme is set to is_available=False, THE System SHALL exclude that theme from the list presented to Clients but preserve existing Event_Bookings referencing that theme

### Requirement 7: Event Status Lifecycle

**User Story:** As a client, I want to know when my pet's party is confirmed and completed, so that I can anticipate the celebration.

#### Acceptance Criteria

1. THE Event_Booking SHALL enforce the following status transitions: pending → confirmed, pending → cancelled, confirmed → completed, confirmed → cancelled
2. WHEN a Staff member confirms an Event_Booking (pending → confirmed), THE System SHALL send a Notification to the Client indicating the event is confirmed for the scheduled date and time
3. WHEN a Staff member marks an Event_Booking as completed, THE System SHALL send a Notification to the Client indicating the event has concluded
4. WHEN a Client cancels an Event_Booking with status "pending", THE System SHALL transition the status to "cancelled" and send a confirmation Notification
5. IF a Client attempts to cancel an Event_Booking with status "confirmed" or "completed", THEN THE System SHALL reject the cancellation and return an error message indicating that confirmed events cannot be cancelled by the Client
6. THE Event_Booking SHALL only allow Staff to transition from "confirmed" to "completed"

### Requirement 8: Live Camera Stream Access

**User Story:** As a client, I want to watch a live camera feed of my pet's suite or play area during their stay, so that I can check on my pet remotely at any time.

#### Acceptance Criteria

1. WHEN a Client requests access to a live camera stream with a valid Reservation, THE System SHALL generate a Stream_Access record with a unique cryptographic Access_Token and an expiration time of 2 hours from generation
2. THE System SHALL validate that the Client's Reservation has status "approved" before granting stream access
3. THE System SHALL validate that the requested Camera is mapped to the location assigned to the Client's Reservation (matching location_type and location_identifier)
4. THE System SHALL validate that the Camera has is_active set to True before granting stream access
5. WHEN a new Stream_Access is generated for a (Reservation, Camera) pair that already has an active unexpired Stream_Access, THE System SHALL revoke the previous access (set is_active to False) before creating the new one
6. THE Stream_Access SHALL provide the Client with an HLS_Stream URL and the Access_Token required for authenticated playback
7. IF a Client requests stream access for a Reservation that does not belong to them, THEN THE System SHALL reject the request with a 403 Forbidden response
8. IF a Client requests stream access for a Camera not mapped to their Reservation location, THEN THE System SHALL reject the request and return an error message indicating no camera is available for their location

### Requirement 9: Camera Administration

**User Story:** As an admin, I want to manage the IP cameras installed at VIPet, so that I can configure which cameras serve which areas and maintain streaming infrastructure.

#### Acceptance Criteria

1. THE Admin SHALL be able to create a Camera with: name (maximum 100 characters), location type (suite, play_area, pool, or garden), location identifier (maximum 50 characters), RTSP URL (maximum 500 characters), optional HLS URL (maximum 500 characters), and active status
2. THE System SHALL enforce uniqueness on the combination of location_type and location_identifier for Camera records
3. THE Admin SHALL be able to deactivate a Camera by setting is_active to False, which immediately prevents new Stream_Access generation for that Camera
4. WHEN a Camera is deactivated, THE System SHALL revoke all active Stream_Access records for that Camera by setting their is_active to False
5. IF the Admin attempts to create a Camera with a duplicate (location_type, location_identifier) combination, THEN THE System SHALL reject the creation and return an error message identifying the conflict

### Requirement 10: Daily Media Updates Upload

**User Story:** As a staff member, I want to upload daily photos and videos of pets during their stay, so that clients can see how their pet is doing.

#### Acceptance Criteria

1. WHEN a Staff member uploads a media file with a valid Reservation, Pet, media type (photo or video), and optional caption, THE System SHALL create a Media_Update record and store the file in media storage
2. THE Media_Update SHALL validate that the Reservation has status "approved" (the pet is currently at VIPet)
3. THE Media_Update SHALL validate that the specified Pet is linked to the specified Reservation
4. THE Media_Update SHALL validate that the uploader has is_staff=True or role "admin"
5. WHEN media_type is "photo", THE Media_Update SHALL accept only JPEG, PNG, or WEBP formats with a maximum file size of 10 MB
6. WHEN media_type is "video", THE Media_Update SHALL accept only MP4 format with a maximum file size of 100 MB and a maximum duration of 60 seconds
7. WHEN a Media_Update is successfully created, THE System SHALL queue an asynchronous task to generate a thumbnail image for the uploaded file
8. WHEN a Media_Update is successfully created, THE System SHALL send a Notification to the Reservation's Client indicating that new media is available for their pet
9. IF a Staff member uploads a file that exceeds the size or format constraints, THEN THE System SHALL reject the upload and return an error message indicating the specific validation failure (file too large, invalid format, or duration exceeded)

### Requirement 11: Media Gallery for Clients

**User Story:** As a client, I want to view all photos and videos taken of my pet during their stay in a gallery, so that I can enjoy the memories and share them.

#### Acceptance Criteria

1. WHEN a Client requests media updates for a Reservation, THE System SHALL return all Media_Update records linked to that Reservation, sorted by creation date descending, paginated at 20 items per page
2. THE System SHALL only allow a Client to view Media_Updates for Reservations belonging to that Client
3. THE System SHALL display each Media_Update with: thumbnail (when available), media type indicator, caption, and upload timestamp
4. WHEN a Client requests a specific Media_Update detail, THE System SHALL return the full media file URL, caption, media type, file size, duration (for videos), and upload timestamp
5. IF a Client has no Media_Updates for a given Reservation, THEN THE System SHALL return an empty list with a message indicating no media is available yet

### Requirement 12: Premium Services Integration with Cart

**User Story:** As a client, I want to add premium services to my cart and pay for them through the existing checkout flow, so that I can combine all my bookings into a single payment.

#### Acceptance Criteria

1. WHEN a Client adds a Transport_Booking to the cart, THE Cart SHALL create a Cart_Item with the transport service reference, the associated Pet, the scheduled date as start_date, and the Transport_Booking price as the unit price
2. WHEN a Client adds an Event_Booking to the cart, THE Cart SHALL create a Cart_Item with the event service reference, the associated Pet, the event date as start_date, and the Event_Booking total_price as the unit price
3. THE Pricing_Engine SHALL apply loyalty discounts and promotional discounts to premium service Cart_Items following the same calculation order as standard services (dynamic pricing does not apply to non-boarding premium services)
4. WHEN an Order is successfully created containing premium service Cart_Items, THE System SHALL update the associated Transport_Booking or Event_Booking status to reflect the paid state
5. IF a premium service booking referenced by a Cart_Item is cancelled before checkout, THEN THE Cart SHALL flag that item as unavailable and exclude it from the cart total

### Requirement 13: Premium Services Notifications

**User Story:** As a client, I want to receive timely notifications about my premium service bookings, so that I stay informed about transport, events, and new media without having to check manually.

#### Acceptance Criteria

1. WHEN a Transport_Booking status changes, THE System SHALL create a Notification for the Client with a message describing the new status within 5 seconds of the status change
2. WHEN an Event_Booking is confirmed by Staff, THE System SHALL create a Notification for the Client with the event theme, date, and time
3. WHEN a new Media_Update is uploaded for a Client's Reservation, THE System SHALL create a Notification for the Client indicating new media is available
4. WHEN a Stream_Access token is about to expire (within 10 minutes of expiration), THE System SHALL create a Notification for the Client suggesting they refresh their stream access
5. THE System SHALL use the existing Notification model and delivery mechanism (in-app notification list) for all premium service notifications

### Requirement 14: Premium Services Access Control

**User Story:** As the platform, I want to ensure that only authorized users can access and manage premium services, so that client data and operations remain secure.

#### Acceptance Criteria

1. THE System SHALL restrict Transport_Booking creation, viewing, and cancellation to the Client who owns the associated Reservation
2. THE System SHALL restrict Event_Booking creation, viewing, and cancellation to the Client who owns the associated Reservation
3. THE System SHALL restrict Media_Update upload to users with is_staff=True or role "admin"
4. THE System SHALL restrict Media_Update viewing to the Client who owns the associated Reservation
5. THE System SHALL restrict Stream_Access generation and usage to the Client who owns the associated Reservation
6. THE System SHALL restrict Van management, Camera management, Event_Theme and Event_Tier management, and Transport_Booking status advancement to users with role "admin" or is_staff=True
7. IF an unauthenticated user attempts to access any premium service endpoint, THEN THE System SHALL return a 401 Unauthorized response
8. IF an authenticated Client attempts to access a premium service resource belonging to another Client, THEN THE System SHALL return a 403 Forbidden response without revealing the existence of the resource
