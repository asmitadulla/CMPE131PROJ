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
    star_rating: Optional[int] = None,
) -> list:
    """
    Searches for hotels via the Booking.com RapidAPI.

    Steps:
      1. Resolves the city to a dest_id via get_destination()
      2. Builds query params including occupancy (adults + children with ages)
      3. Appends Booking.com category filter IDs for pool and star rating
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
    # hotelfacility::11 = swimming pool, class::N = N-star rating
    filter_ids = []
    if has_pool:
        filter_ids.append("hotelfacility::11")
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


async def search_attractions(
    city: str,
    is_theme_park: Optional[bool] = None,
    budget_max: Optional[float] = None,
) -> list:
    """
    Searches for attractions and activities near a city via the Booking.com RapidAPI.

    Steps:
      1. Resolves the city to lat/lng coordinates via get_destination()
      2. Calls the attraction search endpoint with those coordinates
      3. Optionally filters results to theme parks only (for bundle creation)
      4. Optionally filters by price per person

    Returns up to 10 results. Returns an empty list if the city can't be
    resolved, coordinates are missing, or the API fails.
    """
    dest = await get_destination(city)
    if not dest:
        return []

    latitude = dest.get("latitude")
    longitude = dest.get("longitude")
    if not latitude or not longitude:
        return []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/attraction/search",
            params={"latitude": latitude, "longitude": longitude, "locale": "en-gb"},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    # The API nests results under results.attractions
    attractions = data.get("results", {}).get("attractions", [])

    # Filter for theme parks by checking the name and subcategory fields
    if is_theme_park is True:
        attractions = [
            a for a in attractions
            if "theme park" in a.get("name", "").lower()
            or "theme" in str(a.get("subcategory", [])).lower()
        ]

    # representativePrice.publicAmount is the per-person price shown on Booking.com
    if budget_max is not None:
        attractions = [
            a for a in attractions
            if float(
                a.get("representativePrice", {}).get("publicAmount", 0) or 0
            ) <= budget_max
        ]

    return attractions[:10]


async def search_flights(
    departure_city: str,
    arrival_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 2,
    children: int = 0,
) -> dict:
    """
    Searches for flights via the Booking.com RapidAPI.
    Automatically selects the one-way or round-trip endpoint based on
    whether return_date is provided.

    Steps:
      1. Resolves both cities to dest_ids via get_destination()
      2. Builds query params with passenger counts
      3. Calls the appropriate flight search endpoint

    Returns the raw API response dict, or an error dict if cities can't be resolved.
    """
    from_dest = await get_destination(departure_city)
    to_dest = await get_destination(arrival_city)

    if not from_dest or not to_dest:
        return {"flights": [], "message": "Could not resolve city destinations"}

    from_id = from_dest.get("dest_id", "")
    to_id = to_dest.get("dest_id", "")

    params = {
        "from_id": f"city:{from_id}",
        "to_id": f"city:{to_id}",
        "departure_date": departure_date,
        "adults": adults,
        "locale": "en-gb",
        "currency_code": "USD",
    }

    if children > 0:
        params["children"] = children

    # Choose one-way vs round-trip endpoint
    endpoint = "roundtrip" if return_date else "oneway"
    if return_date:
        params["return_date"] = return_date

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/v1/flights/search-{endpoint}",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()
