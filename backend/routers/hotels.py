from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services import rapidapi

router = APIRouter()

MAX_PASSENGERS = 10


@router.get("/search", summary="Search family-friendly hotels")
async def search_hotels(
    city: str = Query(..., description="Destination city name"),
    checkin_date: str = Query(..., description="Check-in date (YYYY-MM-DD)"),
    checkout_date: str = Query(..., description="Check-out date (YYYY-MM-DD)"),
    adults: int = Query(2, ge=1, description="Number of adult passengers (min 1)"),
    children: int = Query(2, ge=0, le=8, description="Number of child passengers"),
    children_ages: str = Query("9,16", description="Comma-separated ages of children"),
    budget_max: Optional[float] = Query(None, description="Maximum total price (USD)"),
    has_pool: bool = Query(False, description="Filter: hotel must have a pool"),
    is_family_friendly: bool = Query(False, description="Filter: family-friendly hotels only"),
    star_rating: Optional[int] = Query(None, ge=1, le=5, description="Minimum star rating"),
    db: Session = Depends(get_db),
):
    """
    Search hotels via Booking.com (RapidAPI).

    Supports multi-passenger occupancy (adults + children), family-specific
    filters (pool, family-friendly), star rating, and budget cap — matching
    the Phase 1 acceptance criteria for the Family Vacationist scenario.
    """
    if adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if adults + children > MAX_PASSENGERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PASSENGERS} total passengers per search",
        )

    # Validate children_ages if children provided
    if children > 0 and children_ages:
        for age_str in children_ages.split(","):
            try:
                age = int(age_str.strip())
                if age < 0:
                    raise ValueError
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid child age '{age_str.strip()}'. Ages must be non-negative integers.",
                )

    try:
        results = await rapidapi.search_hotels(
            city=city,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            adults=adults,
            children=children,
            children_ages=children_ages,
            budget_max=budget_max,
            has_pool=has_pool,
            star_rating=star_rating,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Hotel search service unavailable: {str(e)}")

    if not results:
        return {
            "results": [],
            "count": 0,
            "message": "No Results Found",
            "filters_applied": {
                "city": city,
                "adults": adults,
                "children": children,
                "budget_max": budget_max,
                "has_pool": has_pool,
                "star_rating": star_rating,
            },
        }

    return {
        "results": results,
        "count": len(results),
        "filters_applied": {
            "city": city,
            "adults": adults,
            "children": children,
            "budget_max": budget_max,
            "has_pool": has_pool,
            "star_rating": star_rating,
        },
    }
