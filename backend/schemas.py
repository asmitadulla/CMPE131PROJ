from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# --- Agency (Tenant) ---

class AgencyCreate(BaseModel):
    name: str
    domain: str
    theme_settings: dict = {}

class AgencyResponse(BaseModel):
    agency_id: int
    name: str
    domain: str
    theme_settings: dict
    max_passengers: int
    max_bundles_per_user: int

    model_config = {"from_attributes": True}


# --- Auth ---

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    agency_id: int

class UserLogin(BaseModel):
    email: str
    password: str
    agency_id: int

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    agency_id: int

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# --- Booking ---

class BookingCreate(BaseModel):
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

class BookingResponse(BaseModel):
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
    status: str
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}

class BookingStatusUpdate(BaseModel):
    status: str


# --- Bundle ---

class BundleCreate(BaseModel):
    hotel_id: int
    activity_id: int
    agency_id: int
    name: str
    description: Optional[str] = None
    price: float
    includes_theme_park: bool = False

class BundleResponse(BaseModel):
    bundle_id: int
    hotel_id: int
    activity_id: int
    agency_id: int
    name: str
    price: float
    includes_theme_park: bool
    is_available: bool

    model_config = {"from_attributes": True}
