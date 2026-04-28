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
    departure_city: str = Query(..., description="Departure city name"),
    arrival_city: str = Query(..., description="Arrival/destination city name"),
    departure_date: str = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[str] = Query(None, description="Return date for round-trip (YYYY-MM-DD)"),
    adults: int = Query(2, ge=1, description="Number of adult passengers (min 1)"),
    children: int = Query(2, ge=0, description="Number of child passengers"),
    budget_max: Optional[float] = Query(None, description="Maximum total price (USD)"),
    db: Session = Depends(get_db),
):
    """
    Searches for flights via the Booking.com RapidAPI.

    Omit return_date for a one-way search.
    Include return_date for a round-trip search.
    Default occupancy is 2 adults + 2 children to match the Family Vacationist scenario.
    """
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
