# =============================================================================
# routers/bookings.py
#
# Booking persistence and management endpoints — Group 2 Booking & Persistence APIs.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
from schemas import BookingCreate, BookingResponse, BookingStatusUpdate
from routers.auth import get_current_user

router = APIRouter()

VALID_STATUSES = {"Pending", "Confirmed", "Cancelled"}
MAX_ACTIVE_BOOKINGS = 5


@router.post("/", response_model=BookingResponse, summary="Create a booking (Book Now)")
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if booking.adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")

    if not booking.hotel_id and not booking.bundle_id:
        raise HTTPException(
            status_code=400,
            detail="A booking must include at least a hotel or a bundle selection",
        )

    agency = db.query(models.Agency).filter(models.Agency.agency_id == booking.agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")

    agency_max_passengers = agency.max_passengers or 10
    if booking.adults + booking.children > agency_max_passengers:
        raise HTTPException(
            status_code=400,
            detail=f"This agency allows a maximum of {agency_max_passengers} passengers per booking",
        )

    if booking.bundle_id:
        bundle = db.query(models.Bundle).filter(
            models.Bundle.bundle_id == booking.bundle_id
        ).first()

        if not bundle:
            raise HTTPException(status_code=404, detail="Bundle not found")

        if not bundle.is_available:
            raise HTTPException(
                status_code=400,
                detail="Selected bundle is not available — it is sold out",
            )

        if bundle.start_date and booking.check_in_date < bundle.start_date:
            raise HTTPException(
                status_code=400,
                detail=f"Bundle is not available before {bundle.start_date}",
            )

        if bundle.end_date and booking.check_in_date > bundle.end_date:
            raise HTTPException(
                status_code=400,
                detail=f"Bundle is not available after {bundle.end_date}",
            )

    agency_booking_limit = agency.max_bundles_per_user or MAX_ACTIVE_BOOKINGS
    active_count = db.query(models.Booking).filter(
        models.Booking.user_id == booking.user_id,
        models.Booking.agency_id == booking.agency_id,
        models.Booking.status != "Cancelled",
    ).count()

    if active_count >= agency_booking_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {agency_booking_limit} active bookings per user for this agency",
        )

    db_booking = models.Booking(
        user_id=booking.user_id,
        agency_id=booking.agency_id,
        hotel_id=booking.hotel_id,
        flight_id=booking.flight_id,
        bundle_id=booking.bundle_id,
        total_price=booking.total_price,
        check_in_date=booking.check_in_date,
        check_out_date=booking.check_out_date,
        adults=booking.adults,
        children=booking.children,
        children_ages=booking.children_ages,
        status="Pending",
    )

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/user/{user_id}", response_model=List[BookingResponse], summary="Get user bookings dashboard")
def get_user_bookings(
    user_id: int = Path(..., example=1),
    agency_id: int = Query(..., example=4),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.agency_id == agency_id,
    ).all()


@router.get("/", response_model=List[BookingResponse], summary="Get all bookings for current agency")
def get_agency_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns all bookings for the logged-in user's agency.
    Intended for agency staff/admin dashboard views.
    """
    user_role = getattr(current_user, "role", "customer")

    if user_role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Only agency staff can view all bookings")

    return db.query(models.Booking).filter(
        models.Booking.agency_id == current_user.agency_id
    ).all()


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get a booking by ID")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booking = db.query(models.Booking).filter(
        models.Booking.booking_id == booking_id,
        models.Booking.agency_id == current_user.agency_id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return booking


@router.patch("/{booking_id}/status", response_model=BookingResponse, summary="Update booking status")
def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if status_update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    booking = db.query(models.Booking).filter(
        models.Booking.booking_id == booking_id,
        models.Booking.agency_id == current_user.agency_id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = status_update.status
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/{booking_id}/cancel", response_model=BookingResponse, summary="Cancel a booking")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booking = db.query(models.Booking).filter(
        models.Booking.booking_id == booking_id,
        models.Booking.agency_id == current_user.agency_id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    return booking
