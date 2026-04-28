from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services import rapidapi

router = APIRouter()

MAX_PASSENGERS = 9  # Standard airline limit


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
    Search flights via Booking.com (RapidAPI).

    Supports multi-passenger search for families. At least 1 adult required.
    Omit return_date for one-way; include it for round-trip.
    """
    if adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if adults + children > MAX_PASSENGERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PASSENGERS} passengers per flight booking",
        )

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
