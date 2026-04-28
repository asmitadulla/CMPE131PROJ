# =============================================================================
# routers/attractions.py
#
# Attractions/activities search endpoint — Group 1 Search API.
#
# Endpoint:
#   GET /api/v1/attractions/search
#
# Calls the Booking.com API via services/rapidapi.py and returns a list of
# attractions near the specified city. Returns at least 3 popular activities
# as required by the project spec.
#
# Supports the Family Vacationist bundle scenario:
#   - is_theme_park=true filters results to theme parks only
#   - budget_max filters by per-person price
#   - Results are used to build hotel + theme park ticket bundles
# =============================================================================

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
    start_date: Optional[str] = Query(None, description="Start of availability window (YYYY-MM-DD). Defaults to today."),
    end_date: Optional[str] = Query(None, description="End of availability window (YYYY-MM-DD). Defaults to 30 days from today."),
    db: Session = Depends(get_db),
):
    """
    Searches for attractions and activities via the Booking.com RapidAPI.

    Returns up to 10 results. Use is_theme_park=true to filter specifically
    for theme parks when building hotel + theme park ticket bundles.
    Returns "No Results Found" if no attractions match the criteria.
    """
    # --- Call the RapidAPI service ---
    try:
        results = await rapidapi.search_attractions(
            city=city,
            is_theme_park=is_theme_park,
            budget_max=budget_max,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Attractions service unavailable: {str(e)}")

    # Return a clear "No Results Found" message instead of a plain empty array
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
            "start_date": start_date,
            "end_date": end_date,
        },
    }
