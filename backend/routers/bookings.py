# =============================================================================
# routers/bookings.py
#
# Booking persistence and management endpoints — Group 2 Booking & Persistence APIs.
#
# All endpoints require a valid JWT token (Authorization: Bearer <token>).
# Get a token from POST /api/v1/auth/login or /signup.
#
# Endpoints:
#   POST   /api/v1/bookings/                      — Create a booking (Book Now)
#   GET    /api/v1/bookings/user/{user_id}         — Get all bookings for a user (dashboard)
#   GET    /api/v1/bookings/{booking_id}           — Get a single booking by ID
#   PATCH  /api/v1/bookings/{booking_id}/status    — Update booking status
#   PATCH  /api/v1/bookings/{booking_id}/cancel    — Cancel a booking
#
# Booking lifecycle:  Pending → Confirmed → Cancelled
# Records are never deleted — cancelled bookings stay in the DB for audit history.
# Tenant isolation is enforced by filtering queries on both user_id AND agency_id.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
from schemas import BookingCreate, BookingResponse, BookingStatusUpdate
from routers.auth import get_current_user

router = APIRouter()

VALID_STATUSES = {"Pending", "Confirmed", "Cancelled"}
MAX_ACTIVE_BOOKINGS = 5  # per user, per agency — matches Phase 1 AC3 boundary


@router.post("/", response_model=BookingResponse, summary="Create a booking (Book Now)")
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # requires valid JWT
):
    """
    Persists a new booking to the database when the user clicks 'Book Now'.
    This is the core persistence layer of the application.

    Validations (Phase 1 Acceptance Criteria):
      - At least 1 adult passenger required
      - Total passengers cannot exceed 10
      - If a bundle is selected, it must exist and be marked as available
      - User cannot exceed MAX_ACTIVE_BOOKINGS non-cancelled bookings per agency

    New bookings always start with status = "Pending".
    """
    if booking.adults < 1:
        raise HTTPException(status_code=400, detail="At least 1 adult passenger is required")
    if booking.adults + booking.children > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 passengers per booking")

    # Verify bundle availability if the user selected a bundle
    if booking.bundle_id:
        bundle = db.query(models.Bundle).filter(
            models.Bundle.bundle_id == booking.bundle_id
        ).first()
        if not bundle:
            raise HTTPException(status_code=404, detail="Bundle not found")
        if not bundle.is_available:
            # Sold-out bundles block checkout per Phase 1 AC2 for User Story 2
            raise HTTPException(
                status_code=400,
                detail="Selected bundle is not available for the chosen travel dates",
            )

    # Count active (non-cancelled) bookings for this user under this agency
    # This enforces the per-agency booking limit from Phase 1 AC3
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
    current_user: models.User = Depends(get_current_user),  # requires valid JWT
):
    """
    Returns all bookings for a user — powers the User Dashboard.
    Filters by both user_id AND agency_id to enforce tenant isolation:
    users from Agency A cannot see bookings belonging to Agency B.
    """
    return db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.agency_id == agency_id,
    ).all()


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get a booking by ID")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # requires valid JWT
):
    """Returns the full details of a single booking record."""
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch("/{booking_id}/status", response_model=BookingResponse, summary="Update booking status")
def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # requires valid JWT
):
    """
    Manages the booking lifecycle by updating the status field.
    Valid transitions: Pending → Confirmed → Cancelled.
    Rejects any status value not in the allowed set.
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
    current_user: models.User = Depends(get_current_user),  # requires valid JWT
):
    """
    Cancels a booking by setting its status to 'Cancelled'.
    The record is NOT deleted — it remains in the database for booking
    history and auditing purposes, accessible from the User Dashboard.
    """
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    return booking
