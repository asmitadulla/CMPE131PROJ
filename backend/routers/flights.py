# =============================================================================
# routers/flights.py
#
# Flight search endpoint — Group 1 Search API.
#
# Endpoint:
#   GET /api/v1/flights/search
#
# Calls the Booking.com API via services/rapidapi.py and returns available
# flights between two cities. Supports multi-passenger search for families
# (adults + children). Automatically selects one-way or round-trip based
# on whether return_date is provided.
#
# Validation enforces Phase 1 acceptance criteria:
#   - At least 1 adult required to proceed
#   - Maximum 9 passengers per booking (standard airline limit)
#   - Returns error message if cities cannot be resolved
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services import rapidapi

router = APIRouter()

MAX_PASSENGERS = 9  # Standard airline booking limit per reservation


@router.get("/search", summary="Search flights for multi-passenger families")
async def search_flights(
    departure_city: str = Query(..., description="Departure city name", example="San Jose"),
    arrival_city: str = Query(..., description="Arrival/destination city name", example="Orlando"),
    departure_date: str = Query(..., description="Departure date (YYYY-MM-DD)", example="2026-07-01"),
    return_date: Optional[str] = Query(None, description="Return date for round-trip (YYYY-MM-DD)", example="2026-07-08"),
    adults: Optional[int] = Query(None, description="Number of adult passengers (min 1)", example=2),
    children: Optional[int] = Query(None, description="Number of child passengers", example=2),
    budget_max: Optional[float] = Query(None, description="Maximum total price (USD)", example=3000),
    db: Session = Depends(get_db),
):
    """
    Searches for flights via the Booking.com RapidAPI.

    Omit return_date for a one-way search.
    Include return_date for a round-trip search.
    Default occupancy is 2 adults + 2 children to match the Family Vacationist scenario.
    """
    adults = adults if adults is not None else 2
    children = children if children is not None else 2

    # --- Input validation ---

    if adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if adults + children > MAX_PASSENGERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PASSENGERS} passengers per flight booking",
        )

    # --- Call the RapidAPI service ---
    try:
        results = await rapidapi.search_flights(
            departure_city=departure_city,
            arrival_city=arrival_city,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            children=children,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Flight search service unavailable: {str(e)}")

    return {
        "results": results,
        "filters_applied": {
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
            "children": children,
            "budget_max": budget_max,
        },
    }
