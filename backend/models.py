# =============================================================================
# models.py
#
# SQLAlchemy ORM models — each class maps to a database table.
# These match the ERD designed in Phase 1.
#
# Tables:
#   Agency   — Tenant table. Each travel agency is a separate tenant whose
#              data is fully isolated from other agencies.
#   User     — Platform users, each scoped to one agency via agency_id.
#   Hotel    — Cache/reference table for hotel data pulled from RapidAPI.
#   Flight   — Cache/reference table for flight data pulled from RapidAPI.
#   Activity — Cache/reference table for attractions/theme parks from RapidAPI.
#   Bundle   — Links a Hotel + Activity into a package (e.g. hotel + theme park).
#   Booking  — Transaction record created when a user clicks "Book Now".
#              Lifecycle: Pending → Confirmed → Cancelled.
# =============================================================================

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Agency(Base):
    """
    Represents a travel agency (tenant) in the multi-tenant system.
    All user and booking data is scoped to an agency via foreign keys,
    which enforces data isolation between tenants.
    """
    __tablename__ = "agencies"

    agency_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)  # e.g. "besttravel.com"
    theme_settings = Column(JSON, default={})                  # stores CSS branding vars
    max_passengers = Column(Integer, default=10)               # agency-level passenger cap
    max_bundles_per_user = Column(Integer, default=5)          # agency-level bundle limit

    # Relationships — allow SQLAlchemy to join related rows automatically
    users = relationship("User", back_populates="agency")
    hotels = relationship("Hotel", back_populates="agency")
    bundles = relationship("Bundle", back_populates="agency")
    bookings = relationship("Booking", back_populates="agency")


class User(Base):
    """
    A customer or agent registered under a specific agency.
    Email uniqueness is enforced per-agency, not globally, so the same
    email can exist in two different tenants without conflict.
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash, never plain text
    role = Column(String(50), default="customer")        # "customer" or "agent"

    agency = relationship("Agency", back_populates="users")
    bookings = relationship("Booking", back_populates="user")


class Hotel(Base):
    """
    Cache/reference table for hotel data fetched from the Booking.com RapidAPI.
    Storing this locally allows bookings to reference hotel details without
    making a live API call at booking time.
    """
    __tablename__ = "hotels"

    hotel_id = Column(Integer, primary_key=True, index=True)
    external_hotel_id = Column(String(255))          # ID from Booking.com API
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"))
    name = Column(String(255), nullable=False)
    city = Column(String(255))
    capacity = Column(Integer, default=4)            # max guests the hotel room supports
    amenities = Column(JSON, default=[])             # list of amenity strings
    price_per_night = Column(Float, nullable=False)
    star_rating = Column(Float)
    has_pool = Column(Boolean, default=False)        # key filter for Family Vacationist
    is_family_friendly = Column(Boolean, default=False)
    image_url = Column(String(500))

    agency = relationship("Agency", back_populates="hotels")
    bundles = relationship("Bundle", back_populates="hotel")
    bookings = relationship("Booking", back_populates="hotel")


class Flight(Base):
    """
    Cache/reference table for flight data fetched from the Booking.com RapidAPI.
    Stores the passenger counts so a booking can reconstruct what was searched.
    """
    __tablename__ = "flights"

    flight_id = Column(Integer, primary_key=True, index=True)
    external_flight_id = Column(String(255))
    departure_city = Column(String(255))
    arrival_city = Column(String(255))
    departure_date = Column(String(50))
    return_date = Column(String(50))          # null for one-way flights
    price = Column(Float, nullable=False)
    adults = Column(Integer, default=2)
    children = Column(Integer, default=0)
    airline = Column(String(255))

    bookings = relationship("Booking", back_populates="flight")


class Activity(Base):
    """
    Cache/reference table for attractions and theme parks fetched from
    the Booking.com RapidAPI. The is_theme_park flag drives bundle filtering
    for the Family Vacationist scenario (hotel + theme park tickets).
    """
    __tablename__ = "activities"

    activity_id = Column(Integer, primary_key=True, index=True)
    external_activity_id = Column(String(255))
    name = Column(String(255), nullable=False)
    age_group = Column(String(100))           # e.g. "All ages", "12+"
    price = Column(Float, nullable=False)
    restrictions = Column(Text)               # height/age restrictions, etc.
    is_theme_park = Column(Boolean, default=False)
    city = Column(String(255))
    description = Column(Text)
    image_url = Column(String(500))

    bundles = relationship("Bundle", back_populates="activity")


class Bundle(Base):
    """
    A packaged deal combining a Hotel and an Activity (e.g. hotel + theme park tickets).
    Bundles are scoped to an agency, so different agencies can offer different packages.
    The includes_theme_park flag is used by the UI to filter bundle types.
    """
    __tablename__ = "bundles"

    bundle_id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.hotel_id"))
    activity_id = Column(Integer, ForeignKey("activities.activity_id"))
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    includes_theme_park = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)  # set to False for sold-out bundles

    hotel = relationship("Hotel", back_populates="bundles")
    activity = relationship("Activity", back_populates="bundles")
    agency = relationship("Agency", back_populates="bundles")
    bookings = relationship("Booking", back_populates="bundle")


class Booking(Base):
    """
    A transaction record created when the user clicks 'Book Now'.
    Tracks the full booking lifecycle: Pending → Confirmed → Cancelled.
    Records are never deleted — cancelled bookings remain for audit history.
    Both agency_id and user_id are stored for strict tenant isolation.
    """
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.hotel_id"), nullable=True)
    flight_id = Column(Integer, ForeignKey("flights.flight_id"), nullable=True)
    bundle_id = Column(Integer, ForeignKey("bundles.bundle_id"), nullable=True)
    total_price = Column(Float, nullable=False)
    check_in_date = Column(String(50))
    check_out_date = Column(String(50))
    adults = Column(Integer, default=2)
    children = Column(Integer, default=0)
    children_ages = Column(String(100))       # comma-separated, e.g. "9,16"
    status = Column(String(50), default="Pending")  # Pending | Confirmed | Cancelled
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="bookings")
    agency = relationship("Agency", back_populates="bookings")
    hotel = relationship("Hotel", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")
    bundle = relationship("Bundle", back_populates="bookings")
