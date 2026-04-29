# =============================================================================
# schemas.py
#
# Pydantic models used for request validation and response serialization.
# These are separate from the SQLAlchemy models in models.py:
#   - "Create" schemas define what the client sends in the request body.
#   - "Response" schemas define what the API returns to the client.
#
# FastAPI uses these automatically to validate incoming data and to
# serialize outgoing data into JSON.
# =============================================================================

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# =============================================================================
# Agency (Tenant)
# =============================================================================

class AgencyCreate(BaseModel):
    """Fields required to register a new travel agency (tenant)."""
    name: str
    domain: str
    theme_settings: dict = {}

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Family Travel Co",
                "domain": "familytravel.com",
                "theme_settings": {}
            }
        }
    }

class AgencyResponse(BaseModel):
    """Fields returned after creating or fetching an agency."""
    agency_id: int
    name: str
    domain: str
    theme_settings: dict
    max_passengers: int
    max_bundles_per_user: int

    model_config = {"from_attributes": True}


# =============================================================================
# Authentication
# =============================================================================

class UserCreate(BaseModel):
    """Fields required to register a new user under an agency."""
    name: str
    email: str
    password: str
    agency_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Hannah Smith",
                "email": "hannah@familytravel.com",
                "password": "password123",
                "agency_id": 4
            }
        }
    }

class UserLogin(BaseModel):
    """Fields required to log in. Agency ID scopes the user to a specific tenant."""
    email: str
    password: str
    agency_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "hannah@familytravel.com",
                "password": "password123",
                "agency_id": 4
            }
        }
    }

class UserResponse(BaseModel):
    """Safe user representation — never exposes password_hash."""
    user_id: int
    name: str
    email: str
    role: str
    agency_id: int

    model_config = {"from_attributes": True}

class Token(BaseModel):
    """JWT response returned after successful login or signup."""
    access_token: str
    token_type: str     # always "bearer"
    user: UserResponse  # embedded user info so the client doesn't need a second request


# =============================================================================
# Booking
# =============================================================================

class BookingCreate(BaseModel):
    """
    Fields required to create a booking (sent when user clicks 'Book Now').
    hotel_id, flight_id, and bundle_id are all optional — a booking can
    reference any combination of them.
    """
    user_id: int
    agency_id: int
    hotel_id: Optional[int] = None
    flight_id: Optional[int] = None
    bundle_id: Optional[int] = None
    total_price: float
    check_in_date: str
    check_out_date: str
    adults: int = 2
    children: int = 0
    children_ages: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": 1,
                "agency_id": 4,
                "hotel_id": 1,
                "flight_id": None,
                "bundle_id": 1,
                "total_price": 1469.00,
                "check_in_date": "2026-07-01",
                "check_out_date": "2026-07-08",
                "adults": 2,
                "children": 2,
                "children_ages": "9,16"
            }
        }
    }

class BookingResponse(BaseModel):
    """Full booking record returned to the client."""
    booking_id: int
    user_id: int
    agency_id: int
    hotel_id: Optional[int]
    flight_id: Optional[int]
    bundle_id: Optional[int]
    total_price: float
    check_in_date: str
    check_out_date: str
    adults: int
    children: int
    children_ages: Optional[str]
    status: str          # Pending | Confirmed | Cancelled
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}

class BookingStatusUpdate(BaseModel):
    """Request body for updating a booking's status."""
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {"status": "Confirmed"}
        }
    }


# =============================================================================
# Bundle
# =============================================================================

class BundleCreate(BaseModel):
    """Fields required to create a hotel + activity bundle."""
    hotel_id: int
    activity_id: int
    agency_id: int
    name: str
    description: Optional[str] = None
    price: float
    includes_theme_park: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "hotel_id": 1,
                "activity_id": 1,
                "agency_id": 4,
                "name": "Orlando Family Bundle — Hotel + Disney Ticket",
                "description": "4-night stay at Swan Resort with single-day Disney base tickets for the whole family.",
                "price": 1469.00,
                "includes_theme_park": True,
                "start_date": "2026-06-01",
                "end_date": "2026-08-31"
            }
        }
    }

class BundleResponse(BaseModel):
    """Bundle record returned to the client."""
    bundle_id: int
    hotel_id: int
    activity_id: int
    agency_id: int
    name: str
    description: Optional[str]
    price: float
    includes_theme_park: bool
    is_available: bool  # False means sold out — client should block checkout
    start_date: Optional[str]
    end_date: Optional[str]

    model_config = {"from_attributes": True}
