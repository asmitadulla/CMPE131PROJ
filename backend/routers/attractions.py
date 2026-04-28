from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services import rapidapi

router = APIRouter()


@router.get("/search", summary="Search attractions and theme parks")
async def search_attractions(
    city: str = Query(..., description="City to search for attractions"),
    is_theme_park: Optional[bool] = Query(None, description="Filter: theme parks only (for bundle filtering)"),
    budget_max: Optional[float] = Query(None, description="Maximum price per person (USD)"),
    db: Session = Depends(get_db),
):
    """
    Search attractions/activities via Booking.com (RapidAPI).

    Returns at least 3 popular activities. Supports theme park filter
    for bundle creation (hotel + theme park tickets).
    """
    try:
        results = await rapidapi.search_attractions(
            city=city,
            is_theme_park=is_theme_park,
            budget_max=budget_max,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Attractions service unavailable: {str(e)}")

    if not results:
        return {
            "results": [],
            "count": 0,
            "message": "No Results Found",
            "city": city,
        }

    return {
        "results": results,
        "count": len(results),
        "city": city,
        "filter_applied": {
            "is_theme_park": is_theme_park,
            "budget_max": budget_max,
        },
    }
