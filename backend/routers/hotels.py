# =============================================================================
# routers/hotels.py
#
# Hotel search endpoint — Group 1 Search API.
#
# Endpoint:
#   GET /api/v1/hotels/search
#
# Calls the Booking.com API via services/rapidapi.py and returns hotel
# results filtered by family-specific criteria defined in Phase 1:
#   - Multi-passenger occupancy (adults + children with ages)
#   - Pool filter (has_pool=true)
#   - Family-friendly filter (is_family_friendly=true → family rooms)
#   - Star rating filter
#   - Budget cap (max total price for the stay)
#   - Exclude hotels with missing amenity data (exclude_missing_amenities=true)
#
# Validation enforces Phase 1 acceptance criteria:
#   - At least 1 adult required
#   - Max 10 total passengers
#   - Child ages must be non-negative integers
#   - Returns "No Results Found" when API returns empty results
#   - Max 3 active filters enforced simultaneously (Phase 1 AC3)
#   - Conflicting filter pairs rejected with a clear error (Phase 1 AC3)
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services import rapidapi

router = APIRouter()

MAX_PASSENGERS = 10


MAX_ACTIVE_FILTERS = 3  # Phase 1 AC3: max simultaneous filters per search
# Booking.com budget threshold below which 4-star+ hotels are considered a conflict
LUXURY_BUDGET_FLOOR = 150.0


@router.get("/search", summary="Search family-friendly hotels")
async def search_hotels(
    city: str = Query(..., description="Destination city name", example="Orlando"),
    checkin_date: str = Query(..., description="Check-in date (YYYY-MM-DD)", example="2026-07-01"),
    checkout_date: str = Query(..., description="Check-out date (YYYY-MM-DD)", example="2026-07-08"),
    adults: Optional[int] = Query(None, description="Number of adult passengers (min 1)", example=2),
    children: Optional[int] = Query(None, description="Number of child passengers", example=2),
    children_ages: Optional[str] = Query(None, description="Comma-separated ages of children", example="9,16"),
    budget_max: Optional[float] = Query(None, description="Maximum total price (USD)", example=2000),
    has_pool: Optional[bool] = Query(None, description="Filter: hotel must have a pool", example=True),
    is_family_friendly: Optional[bool] = Query(None, description="Filter: family rooms / family-friendly hotels", example=True),
    star_rating: Optional[int] = Query(None, ge=1, le=5, description="Minimum star rating", example=4),
    exclude_missing_amenities: Optional[bool] = Query(None, description="Exclude hotels that have no amenity data", example=False),
    db: Session = Depends(get_db),
):
    """
    Searches hotels via the Booking.com RapidAPI with family-specific filters.

    Supports the Family Vacationist scenario (Scenario #7):
    - Default occupancy is 2 adults + 2 children aged 9 and 16
    - has_pool and is_family_friendly target family-friendly accommodations
    - budget_max enforces the user's total stay budget constraint
    - exclude_missing_amenities removes hotels that return no amenity data
    - Max 3 filters active at once (Phase 1 AC3 limit)
    - Conflicting filter combinations (luxury rating + low budget) are rejected
    """
    # Apply defaults here so Swagger shows only Example, not Default value
    adults = adults if adults is not None else 2
    children = children if children is not None else 2
    children_ages = children_ages if children_ages is not None else "9,16"
    has_pool = has_pool if has_pool is not None else False
    is_family_friendly = is_family_friendly if is_family_friendly is not None else False
    exclude_missing_amenities = exclude_missing_amenities if exclude_missing_amenities is not None else False

    # --- Input validation (Phase 1 Acceptance Criteria) ---

    if adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if adults + children > MAX_PASSENGERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PASSENGERS} total passengers per search",
        )

    # Validate each child's age is a non-negative integer
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

    # --- Phase 1 AC3: max filter count enforcement ---
    # Count how many optional filters the caller has activated
    active_filters = sum([
        has_pool,
        is_family_friendly,
        star_rating is not None,
        budget_max is not None,
        exclude_missing_amenities,
    ])
    if active_filters > MAX_ACTIVE_FILTERS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many filters active ({active_filters}). Maximum {MAX_ACTIVE_FILTERS} filters allowed per search.",
        )

    # --- Phase 1 AC3: conflicting filter detection ---
    # A high star rating combined with a very low budget can never be satisfied —
    # flag it early so the user isn't shown a confusing empty result set
    if star_rating is not None and star_rating >= 4 and budget_max is not None and budget_max < LUXURY_BUDGET_FLOOR:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Conflicting filters: {star_rating}-star hotels typically exceed "
                f"${LUXURY_BUDGET_FLOOR:.0f}. Raise budget_max or lower star_rating."
            ),
        )

    # --- Call the RapidAPI service ---
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
            is_family_friendly=is_family_friendly,
            star_rating=star_rating,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Hotel search service unavailable: {str(e)}")

    # exclude_missing_amenities: drop hotels where the API returned no facility data
    if exclude_missing_amenities:
        results = [h for h in results if h.get("hotel_facilities") or h.get("facilities")]

    filters_applied = {
        "city": city,
        "adults": adults,
        "children": children,
        "budget_max": budget_max,
        "has_pool": has_pool,
        "is_family_friendly": is_family_friendly,
        "star_rating": star_rating,
        "exclude_missing_amenities": exclude_missing_amenities,
    }

    # Return a clear "No Results Found" message instead of an empty array
    if not results:
        return {
            "results": [],
            "count": 0,
            "message": "No Results Found",
            "filters_applied": filters_applied,
        }

    return {
        "results": results,
        "count": len(results),
        "filters_applied": filters_applied,
    }
