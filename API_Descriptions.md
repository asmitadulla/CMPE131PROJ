# API Descriptions — Travel Agent SaaS Platform
**Scenario #7: The Family Vacationist | CMPE 131**

Base URL: `http://localhost:8000`
Interactive Docs: `http://localhost:8000/docs`

---

## Group 1: Search APIs

### 1. Hotel Search
**`GET /api/hotels/search`**

Searches for hotels using the Booking.com API (via RapidAPI). Designed for the Family Vacationist scenario — supports multi-passenger occupancy (adults + children with ages), family-friendly amenity filters, pool filter, star rating filter, and budget cap. Returns up to 20 results sorted by popularity. Returns "No Results Found" when no hotels match the criteria.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `city` | string | yes | Destination city name |
| `checkin_date` | string | yes | Check-in date (YYYY-MM-DD) |
| `checkout_date` | string | yes | Check-out date (YYYY-MM-DD) |
| `adults` | integer | yes | Number of adult passengers (min 1) |
| `children` | integer | no | Number of child passengers (default 2) |
| `children_ages` | string | no | Comma-separated ages, e.g. "9,16" |
| `budget_max` | float | no | Maximum total stay price (USD) |
| `has_pool` | boolean | no | Filter for hotels with a pool |
| `is_family_friendly` | boolean | no | Filter for family-friendly hotels |
| `star_rating` | integer | no | Minimum star rating (1–5) |

**Error handling:** Returns 400 if adults < 1, if total passengers > 10, or if child ages are invalid (negative/non-numeric). Returns 503 if the external API is unavailable.

---

### 2. Flight Search
**`GET /api/flights/search`**

Searches for one-way or round-trip flights using the Booking.com API (via RapidAPI). Supports multi-passenger search for families (adults + children). At least 1 adult is required.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `departure_city` | string | yes | Origin city |
| `arrival_city` | string | yes | Destination city |
| `departure_date` | string | yes | Departure date (YYYY-MM-DD) |
| `return_date` | string | no | Return date for round-trip (YYYY-MM-DD) |
| `adults` | integer | yes | Number of adult passengers (min 1) |
| `children` | integer | no | Number of child passengers (default 2) |
| `budget_max` | float | no | Maximum total price (USD) |

**Error handling:** Returns 400 if adults < 1 or total passengers > 9. Returns 503 if the external API is unavailable.

---

### 3. Attractions Search
**`GET /api/attractions/search`**

Searches for activities and attractions using the Booking.com API (via RapidAPI). Supports theme park filtering for bundle creation (hotel + theme park tickets). Returns at least 3 popular activities per city. Supports optional budget filter per person.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `city` | string | yes | City to search for attractions |
| `is_theme_park` | boolean | no | Filter for theme parks only |
| `budget_max` | float | no | Maximum price per person (USD) |

**Error handling:** Returns "No Results Found" message when no attractions match. Returns 503 if the external API is unavailable.

---

## Group 2: Authentication APIs

### 4. Register Agency (Tenant)
**`POST /api/auth/agency`**

Creates a new travel agency as a tenant in the system. Each agency has its own isolated data, branding settings, and passenger/booking limits. No authentication required.

**Request body:** `name`, `domain`, `theme_settings` (optional JSON)

---

### 5. User Signup
**`POST /api/auth/signup`**

Registers a new user under a specific agency. Email uniqueness is enforced per-agency (same email can exist in different tenants). Returns a JWT token on success.

**Request body:** `name`, `email`, `password`, `agency_id`

---

### 6. User Login
**`POST /api/auth/login`**

Authenticates a user under a specific agency and returns a JWT token. The token must be passed as a Bearer token in the `Authorization` header for all booking endpoints.

**Request body:** `email`, `password`, `agency_id`

---

## Group 2: Booking & Persistence APIs

> All booking endpoints require a valid JWT token (`Authorization: Bearer <token>`).

### 7. Create Booking (Book Now)
**`POST /api/bookings/`**

Persists a new booking to the database when the user clicks "Book Now". Always starts with `Pending` status. Validates passenger count, bundle availability, and enforces a maximum of 5 active bookings per user (per agency/tenant).

**Request body:** `user_id`, `agency_id`, `hotel_id`, `flight_id`, `bundle_id`, `total_price`, `check_in_date`, `check_out_date`, `adults`, `children`, `children_ages`

**Error handling:** Returns 400 if no adult passenger, if total passengers > 10, if bundle is unavailable, or if booking limit is exceeded. Returns 404 if bundle not found.

---

### 8. Get User Bookings (Dashboard)
**`GET /api/bookings/user/{user_id}`**

Returns all bookings for a user, scoped to their agency. Implements tenant isolation — users can only view bookings within their own agency. Powers the User Dashboard.

| Parameter | Type | Description |
|---|---|---|
| `user_id` | path | The user's ID |
| `agency_id` | query | The agency ID (enforces tenant isolation) |

---

### 9. Get Booking by ID
**`GET /api/bookings/{booking_id}`**

Returns details of a specific booking by ID.

---

### 10. Update Booking Status
**`PATCH /api/bookings/{booking_id}/status`**

Manages the booking lifecycle: `Pending → Confirmed → Cancelled`. Rejects invalid status values.

**Request body:** `status` — one of `"Pending"`, `"Confirmed"`, `"Cancelled"`

---

### 11. Cancel Booking
**`DELETE /api/bookings/{booking_id}`**

Cancels a booking by setting its status to `Cancelled`. Used by the User Dashboard cancel button.

---

## Database Schema Summary

| Table | Key Fields | Purpose |
|---|---|---|
| `agencies` | agency_id, name, domain, theme_settings | Tenant registry |
| `users` | user_id, agency_id, email, role | Users scoped to a tenant |
| `hotels` | hotel_id, agency_id, amenities, has_pool, star_rating | Hotel cache/reference |
| `flights` | flight_id, departure_city, arrival_city, price | Flight cache/reference |
| `activities` | activity_id, is_theme_park, price | Attractions cache |
| `bundles` | bundle_id, hotel_id, activity_id, includes_theme_park | Hotel + theme park packages |
| `bookings` | booking_id, user_id, agency_id, status, total_price | Booking transactions |

Tenant isolation is enforced via `agency_id` on all user and booking records, and via the `X-Agency-ID` middleware header.
