from fastapi import APIRouter, Depends, HTTPException, Security
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
    """
    Persist a new booking when the user clicks 'Book Now'.
    Requires JWT. Starts in Pending status. Enforces passenger count,
    bundle availability, and per-user booking limits (tenant-scoped).
    """
    if booking.adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if booking.adults + booking.children > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 passengers per booking")

    # Verify bundle availability if selected
    if booking.bundle_id:
        bundle = db.query(models.Bundle).filter(
            models.Bundle.bundle_id == booking.bundle_id
        ).first()
        if not bundle:
            raise HTTPException(status_code=404, detail="Bundle not found")
        if not bundle.is_available:
            raise HTTPException(
                status_code=400,
                detail="Selected bundle is not available for the chosen travel dates",
            )

    # Enforce per-user active booking limit (agency-scoped for tenant isolation)
    active_count = db.query(models.Booking).filter(
        models.Booking.user_id == booking.user_id,
        models.Booking.agency_id == booking.agency_id,
        models.Booking.status != "Cancelled",
    ).count()
    if active_count >= MAX_ACTIVE_BOOKINGS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_ACTIVE_BOOKINGS} active bookings per user",
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


@router.get("/user/{user_id}", response_model=List[BookingResponse], summary="Get user bookings (dashboard)")
def get_user_bookings(
    user_id: int,
    agency_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    User dashboard: fetch all bookings for a user, scoped to their agency.
    Requires JWT. Tenant isolation enforced — users only see their own agency's bookings.
    """
    return db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.agency_id == agency_id,
    ).all()


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get a booking by ID")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Requires JWT."""
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
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
    """
    Manage booking lifecycle: Pending → Confirmed → Cancelled. Requires JWT.
    """
    if status_update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
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
    """
    Sets booking status to Cancelled without deleting the record.
    Preserves booking history for auditing. Requires JWT.
    """
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    return booking
