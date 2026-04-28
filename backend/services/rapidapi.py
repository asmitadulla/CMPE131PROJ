import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "booking-com.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"
TIMEOUT = 30


def _headers():
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }


async def get_destination(city_name: str) -> Optional[dict]:
    """Resolve a city name to a Booking.com dest_id."""
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
    Search hotels via Booking.com RapidAPI.
    Applies occupancy (adults + children), pool filter, star rating, and budget cap.
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

    if children > 0:
        params["children_number"] = children
        if children_ages:
            params["children_ages"] = children_ages

    # Build amenity/class filter IDs
    filter_ids = []
    if has_pool:
        filter_ids.append("hotelfacility::11")  # Booking.com pool facility ID
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

    # Apply budget filter client-side (API returns min_total_price per stay)
    if budget_max is not None:
        hotels = [h for h in hotels if float(h.get("min_total_price", 0) or 0) <= budget_max]

    return hotels[:20]


async def search_attractions(
    city: str,
    is_theme_park: Optional[bool] = None,
    budget_max: Optional[float] = None,
) -> list:
    """
    Search attractions via Booking.com RapidAPI.
    Optionally filter for theme parks to support bundle creation.
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

    # Response shape: {"results": {"attractions": [...]}}
    attractions = data.get("results", {}).get("attractions", [])

    if is_theme_park is True:
        attractions = [
            a for a in attractions
            if "theme park" in a.get("name", "").lower()
            or "theme" in str(a.get("subcategory", [])).lower()
        ]

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
    Search flights via Booking.com RapidAPI (one-way or round-trip).
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
