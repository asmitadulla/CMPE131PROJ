from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
import models
from routers.auth import get_current_user

router = APIRouter()


@router.get("/search", summary="Search recommended travel packages")
def search_recommendations(
    destination: str,
    start_date: str,
    end_date: str,
    budget: float = Query(..., gt=0),
    adults: int = Query(..., ge=1),
    children: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    bundles = db.query(models.Bundle).filter(
        models.Bundle.agency_id == current_user.agency_id,
        models.Bundle.is_available == True,
        models.Bundle.price <= budget
    ).all()

    recommendations = []

    for bundle in bundles:
        recommendations.append({
            "bundle_id": bundle.bundle_id,
            "price": bundle.price,
            "description": bundle.description,
            "within_budget": bundle.price <= budget
        })

    return {
        "destination": destination,
        "count": len(recommendations),
        "recommendations": recommendations
    }
