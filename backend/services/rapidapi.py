# =============================================================================
# services/rapidapi.py
#
# All outbound calls to the Booking.com API via RapidAPI live here.
# Routers never call the external API directly — they always go through
# this service layer, which keeps API logic in one place and makes it
# easy to swap out the provider later if needed.
#
# Functions:
#   get_destination()    — Resolves a city name to a Booking.com dest_id
#   search_hotels()      — Searches hotels with occupancy + family filters
#   search_attractions() — Searches attractions, optionally filtered to theme parks
#   search_flights()     — Searches one-way or round-trip flights
#
# All functions are async and use httpx for non-blocking HTTP requests,
# which is required for FastAPI's async performance model.
# =============================================================================

import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "booking-com.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"
TIMEOUT = 30  # seconds before giving up on an external API call


def _headers():
    """Returns the auth headers required by every RapidAPI request."""
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }


async def get_destination(city_name: str) -> Optional[dict]:
    """
    Resolves a human-readable city name (e.g. "Orlando") into a Booking.com
    destination object that contains dest_id, dest_type, latitude, and longitude.
    These values are required by the hotel and attraction search endpoints.

    Returns the first match from the API, or None if no results.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/hotels/locations",
            params={"name": city_name, "locale": "en-gb"},
            headers=_headers(),
        )
        resp.raise_for_status()
        results = resp.json()
        if isinstance(results, list) and results:
            return results[0]
        return None


async def search_hotels(
    city: str,
    checkin_date: str,
    checkout_date: str,
    adults: int = 2,
    children: int = 0,
    children_ages: str = "",
    budget_max: Optional[float] = None,
    has_pool: bool = False,
    is_family_friendly: bool = False,
    star_rating: Optional[int] = None,
) -> list:
    """
    Searches for hotels via the Booking.com RapidAPI.

    Steps:
      1. Resolves the city to a dest_id via get_destination()
      2. Builds query params including occupancy (adults + children with ages)
      3. Appends Booking.com category filter IDs for pool, family rooms, and star rating
      4. Calls the hotel search endpoint
      5. Applies a client-side budget filter (the API returns min_total_price
         per stay, so we filter after receiving results)

    Returns up to 20 results sorted by popularity.
    Returns an empty list if the city can't be resolved or the API fails.
    """
    dest = await get_destination(city)
    if not dest:
        return []

    dest_id = dest.get("dest_id") or dest.get("id", "")
    dest_type = dest.get("dest_type", "city")

    params = {
        "dest_id": dest_id,
        "dest_type": dest_type,
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "adults_number": adults,
        "room_number": 1,
        "locale": "en-gb",
        "currency": "USD",
        "order_by": "popularity",
        "filter_by_currency": "USD",
        "include_adjacency": "true",
        "page_number": 0,
        "units": "imperial",
    }

    # Only add children params if there are children — some API versions reject
    # children_number=0 as invalid
    if children > 0:
        params["children_number"] = children
        if children_ages:
            params["children_ages"] = children_ages

    # Build the Booking.com categories_filter_ids string
    # hotelfacility::11 = swimming pool
    # hotelfacility::28 = family rooms (maps our is_family_friendly flag)
    # class::N          = N-star rating
    filter_ids = []
    if has_pool:
        filter_ids.append("hotelfacility::11")
    if is_family_friendly:
        filter_ids.append("hotelfacility::28")
    if star_rating:
        filter_ids.append(f"class::{star_rating}")
    if filter_ids:
        params["categories_filter_ids"] = ",".join(filter_ids)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/hotels/search",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    hotels = data.get("result", [])

    # Budget filter is applied here because the API doesn't support a max-price
    # query param — min_total_price is the cheapest available room for the stay
    if budget_max is not None:
        hotels = [h for h in hotels if float(h.get("min_total_price", 0) or 0) <= budget_max]

    return hotels[:20]


THEME_PARK_KEYWORDS = {
    "theme park", "amusement park", "disney", "universal", "seaworld",
    "busch gardens", "six flags", "legoland", "adventure park",
}


async def search_attractions(
    city: str,
    is_theme_park: Optional[bool] = None,
    budget_max: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list:
    """
    Searches for attractions and activities near a city via the Booking.com RapidAPI.

    Steps:
      1. Resolves the city to dest_id + lat/lng via get_destination()
      2. Calls /v1/attractions/search with the required dest_id, lat/lng, and dates
      3. Optionally filters results to theme parks only (for bundle creation)
      4. Optionally filters by price per person

    start_date / end_date default to 30 days from today if not supplied.
    Results are returned under the 'products' key in the API response.
    Returns up to 10 results. Returns an empty list if the city can't be
    resolved, coordinates are missing, or the API fails.
    """
    from datetime import date, timedelta

    dest = await get_destination(city)
    if not dest:
        return []

    latitude = dest.get("latitude")
    longitude = dest.get("longitude")
    dest_id = dest.get("dest_id") or dest.get("id", "")
    if not latitude or not longitude:
        return []

    # The attractions API requires explicit date range — default to next 30 days
    today = date.today()
    s_date = start_date or today.isoformat()
    e_date = end_date or (today + timedelta(days=30)).isoformat()

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/attractions/search",
            params={
                "dest_id": dest_id,
                "latitude": latitude,
                "longitude": longitude,
                "locale": "en-gb",
                "currency": "USD",
                "order_by": "trending",
                "start_date": s_date,
                "end_date": e_date,
            },
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    # API returns results under the 'products' key
    attractions = data.get("products", [])

    # Filter for theme parks by scanning name and description for known keywords
    if is_theme_park is True:
        def _is_theme_park(a: dict) -> bool:
            text = (a.get("name", "") + " " + a.get("shortDescription", "")).lower()
            return any(kw in text for kw in THEME_PARK_KEYWORDS)

        attractions = [a for a in attractions if _is_theme_park(a)]

    # representativePrice.publicAmount is the per-person price shown on Booking.com
    if budget_max is not None:
        attractions = [
            a for a in attractions
            if float(
                a.get("representativePrice", {}).get("publicAmount", 0) or 0
            ) <= budget_max
        ]

    return attractions[:10]


async def get_airport(city_name: str) -> Optional[dict]:
    """
    Resolves a city name to the first matching airport via /v1/flights/locations.
    Returns a dict with 'code' (e.g. 'SJC.AIRPORT') used by the flight search endpoint.
    Returns None if no airport is found for the city.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/flights/locations",
            params={"name": city_name, "locale": "en-gb"},
            headers=_headers(),
        )
        resp.raise_for_status()
        results = resp.json()
        if isinstance(results, list) and results:
            return results[0]
        return None


async def search_flights(
    departure_city: str,
    arrival_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 2,
    children: int = 0,
) -> dict:
    """
    Searches for flights via the Booking.com RapidAPI using /v1/flights/search.

    Steps:
      1. Resolves both cities to airport codes via get_airport() (/v1/flights/locations)
      2. Builds query params with passenger counts, cabin class, and flight type
      3. Calls /v1/flights/search — single endpoint handles both one-way and round-trip
         via the flight_type param (ONEWAY or ROUNDTRIP)

    Returns the raw API response dict, or an error dict if cities can't be resolved.
    Results are under the 'flightOffers' key in the response.
    """
    from_airport = await get_airport(departure_city)
    to_airport = await get_airport(arrival_city)

    if not from_airport or not to_airport:
        return {"flightOffers": [], "message": "Could not resolve city airports"}

    # The flight search requires the full code format: e.g. "SJC.AIRPORT"
    from_code = from_airport.get("code", "")
    to_code = to_airport.get("code", "")

    flight_type = "ROUNDTRIP" if return_date else "ONEWAY"

    params = {
        "from_code": from_code,
        "to_code": to_code,
        "depart_date": departure_date,
        "adults": adults,
        "flight_type": flight_type,
        "cabin_class": "ECONOMY",
        "order_by": "BEST",
        "currency": "USD",
        "locale": "en-gb",
    }

    if children > 0:
        params["children"] = children

    if return_date:
        params["return_date"] = return_date

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/flights/search",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()
