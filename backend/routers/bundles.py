# =============================================================================
# routers/bundles.py
#
# Bundle management endpoints — Group 1 & 2 Bundle APIs.
#
# Bundles combine a Hotel + Activity (e.g. hotel + theme park tickets) into a
# single bookable package. They are scoped per agency for tenant isolation.
#
# Endpoints:
#   POST  /api/v1/bundles/              — Create a new bundle
#   GET   /api/v1/bundles/              — List all available bundles for an agency
#   GET   /api/v1/bundles/compare       — Compare 2-3 bundles side by side
#   GET   /api/v1/bundles/{bundle_id}   — Get a single bundle by ID
#   PATCH /api/v1/bundles/{bundle_id}/availability — Toggle bundle availability
#
# NOTE: /compare is declared before /{bundle_id} so FastAPI doesn't try to
# match the literal string "compare" as a bundle_id integer.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
from schemas import BundleCreate, BundleResponse
from routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=BundleResponse, summary="Create a new hotel + activity bundle")
def create_bundle(
    bundle: BundleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a bundled package combining a hotel and an activity (e.g. theme park).
    Validates that the referenced hotel and activity exist before persisting.
    Bundles start as available by default (is_available=True).
    """
    # Verify the hotel exists before linking it
    hotel = db.query(models.Hotel).filter(models.Hotel.hotel_id == bundle.hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    # Verify the activity exists before linking it
    activity = db.query(models.Activity).filter(models.Activity.activity_id == bundle.activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    db_bundle = models.Bundle(
        hotel_id=bundle.hotel_id,
        activity_id=bundle.activity_id,
        agency_id=bundle.agency_id,
        name=bundle.name,
        description=bundle.description,
        price=bundle.price,
        includes_theme_park=bundle.includes_theme_park,
        is_available=True,
        start_date=bundle.start_date,
        end_date=bundle.end_date,
    )
    db.add(db_bundle)
    db.commit()
    db.refresh(db_bundle)
    return db_bundle


@router.get("/", response_model=List[BundleResponse], summary="List bundles for an agency")
def list_bundles(
    agency_id: int = Query(..., description="Agency ID to filter bundles by tenant", example=4),
    includes_theme_park: Optional[bool] = Query(None, description="Filter: theme park bundles only", example=True),
    available_only: Optional[bool] = Query(None, description="Only return available (non-sold-out) bundles", example=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns all bundles for the specified agency.
    Use includes_theme_park=true to find hotel + theme park ticket packages
    for the Family Vacationist scenario.
    Sold-out bundles are excluded by default (available_only=true).
    """
    available_only = available_only if available_only is not None else True

    query = db.query(models.Bundle).filter(models.Bundle.agency_id == agency_id)

    if available_only:
        query = query.filter(models.Bundle.is_available == True)

    if includes_theme_park is not None:
        query = query.filter(models.Bundle.includes_theme_park == includes_theme_park)

    return query.all()


@router.get("/compare", summary="Compare 2-3 bundles side by side")
def compare_bundles(
    bundle_ids: str = Query(..., description="Comma-separated bundle IDs to compare (2-3 bundles)", example="1,2"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns full details for 2-3 bundles arranged for side-by-side comparison.
    Use this endpoint to help users choose between competing vacation packages.

    Example: /compare?bundle_ids=1,2,3
    """
    id_list = [s.strip() for s in bundle_ids.split(",") if s.strip()]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 bundle IDs are required for comparison")
    if len(id_list) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 bundles can be compared at once")

    # Parse IDs — reject non-integers early with a clear message
    try:
        parsed_ids = [int(i) for i in id_list]
    except ValueError:
        raise HTTPException(status_code=400, detail="bundle_ids must be integers separated by commas")

    bundles = (
        db.query(models.Bundle)
        .filter(models.Bundle.bundle_id.in_(parsed_ids))
        .all()
    )

    if len(bundles) != len(parsed_ids):
        found_ids = {b.bundle_id for b in bundles}
        missing = [i for i in parsed_ids if i not in found_ids]
        raise HTTPException(status_code=404, detail=f"Bundles not found: {missing}")

    # Return structured comparison with price delta highlighted
    prices = [b.price for b in bundles]
    cheapest = min(prices)

    return {
        "bundles": [
            {
                "bundle_id": b.bundle_id,
                "name": b.name,
                "price": b.price,
                "price_vs_cheapest": round(b.price - cheapest, 2),
                "includes_theme_park": b.includes_theme_park,
                "is_available": b.is_available,
                "hotel_id": b.hotel_id,
                "activity_id": b.activity_id,
                "description": b.description,
                "start_date": b.start_date,
                "end_date": b.end_date,
            }
            for b in bundles
        ],
        "count": len(bundles),
    }


@router.get("/{bundle_id}", response_model=BundleResponse, summary="Get a bundle by ID")
def get_bundle(
    bundle_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns the full details of a single bundle, including availability status."""
    bundle = db.query(models.Bundle).filter(models.Bundle.bundle_id == bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.patch("/{bundle_id}/availability", response_model=BundleResponse, summary="Toggle bundle availability")
def update_bundle_availability(
    bundle_id: int,
    is_available: bool = Query(..., description="Set to false to mark the bundle as sold out"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Marks a bundle as available or sold out.
    Sold-out bundles (is_available=false) block checkout per Phase 1 AC2.
    The bundle record is preserved — it can be re-enabled when inventory returns.
    """
    bundle = db.query(models.Bundle).filter(models.Bundle.bundle_id == bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    bundle.is_available = is_available
    db.commit()
    db.refresh(bundle)
    return bundle
