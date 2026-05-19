from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter()


@router.get("/{agency_id}/theme", summary="Get tenant theme settings")
def get_agency_theme(agency_id: int, db: Session = Depends(get_db)):
    agency = db.query(models.Agency).filter(models.Agency.agency_id == agency_id).first()

    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")

    return {
        "agency_id": agency.agency_id,
        "name": agency.name,
        "domain": agency.domain,
        "theme_settings": agency.theme_settings
    }
