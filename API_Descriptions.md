# API Descriptions — Travel Agent SaaS Platform
**Scenario #7: The Family Vacationist | CMPE 131**

Base URL: `http://localhost:8000`
Interactive Docs: `http://localhost:8000/docs`

---

# Group 1: Search APIs

## 1. Hotel Search
**`GET /api/v1/hotels/search`**

Searches for hotels using the Booking.com API (via RapidAPI). Designed for the Family Vacationist scenario — supports multi-passenger occupancy (adults + children with ages), family-friendly amenity filters, pool filter, star rating filter, and budget cap.

Returns up to 20 results sorted by popularity.

Returns `"No Results Found"` when no hotels match the criteria.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `city` | string | yes | Destination city name |
| `checkin_date` | string | yes | Check-in date (YYYY-MM-DD) |
| `checkout_date` | string | yes | Check-out date (YYYY-MM-DD) |
| `adults` | integer | yes | Number of adult passengers (min 1) |
| `children` | integer | no | Number of child passengers |
| `children_ages` | string | no | Comma-separated ages, e.g. `"9,16"` |
| `budget_max` | float | no | Maximum total stay price |
| `has_pool` | boolean | no | Filter hotels with pools |
| `is_family_friendly` | boolean | no | Filter family-friendly hotels |
| `star_rating` | integer | no | Minimum star rating |

### Error Handling
- Returns `400` if:
  - adults < 1
  - invalid child ages
  - passenger count exceeds allowed limit
- Returns `503` if external API unavailable

---

## 2. Flight Search
**`GET /api/v1/flights/search`**

Searches for one-way or round-trip flights using the Booking.com API (via RapidAPI). Supports multi-passenger family travel.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `departure_city` | string | yes | Origin city |
| `arrival_city` | string | yes | Destination city |
| `departure_date` | string | yes | Departure date |
| `return_date` | string | no | Return date |
| `adults` | integer | yes | Number of adults |
| `children` | integer | no | Number of children |
| `budget_max` | float | no | Maximum total price |

### Error Handling
- Returns `400` if adults < 1 or passenger limit exceeded
- Returns `503` if external API unavailable

---

## 3. Attractions Search
**`GET /api/v1/attractions/search`**

Searches for activities and attractions using the Booking.com API (via RapidAPI). Supports theme park filtering for bundle creation.

Returns at least 3 popular attractions per destination city.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `city` | string | yes | Destination city |
| `is_theme_park` | boolean | no | Theme park only filter |
| `budget_max` | float | no | Max attraction price |

### Error Handling
- Returns `"No Results Found"` if no attractions match
- Returns `503` if external API unavailable

---

## 4. Recommendation Search
**`GET /api/v1/recommendations/search`**

Returns recommended vacation bundles filtered by:
- budget
- tenant agency
- availability
- passenger count

Designed specifically for the Family Vacationist scenario.

Requires JWT authentication.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `destination` | string | yes | Destination city |
| `start_date` | string | yes | Travel start date |
| `end_date` | string | yes | Travel end date |
| `budget` | float | yes | Maximum vacation budget |
| `adults` | integer | yes | Number of adults |
| `children` | integer | no | Number of children |

### Response
Returns:
- recommended bundles
- prices
- descriptions
- within-budget flag

---

# Group 2: Authentication APIs

## 5. Register Agency (Tenant)
**`POST /api/v1/auth/agency`**

Creates a new travel agency tenant in the platform.

Each tenant has isolated:
- users
- bookings
- bundles
- branding settings

### Request Body
```json
{
  "name": "Dream Travel",
  "domain": "dreamtravel.com",
  "theme_settings": {}
}
