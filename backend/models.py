from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Agency(Base):
    __tablename__ = "agencies"

    agency_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    theme_settings = Column(JSON, default={})
    max_passengers = Column(Integer, default=10)
    max_bundles_per_user = Column(Integer, default=5)

    users = relationship("User", back_populates="agency")
    hotels = relationship("Hotel", back_populates="agency")
    bundles = relationship("Bundle", back_populates="agency")
    bookings = relationship("Booking", back_populates="agency")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="customer")

    agency = relationship("Agency", back_populates="users")
    bookings = relationship("Booking", back_populates="user")


class Hotel(Base):
    """Cache table for hotel data retrieved from RapidAPI."""
    __tablename__ = "hotels"

    hotel_id = Column(Integer, primary_key=True, index=True)
    external_hotel_id = Column(String(255))
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"))
    name = Column(String(255), nullable=False)
    city = Column(String(255))
    capacity = Column(Integer, default=4)
    amenities = Column(JSON, default=[])
    price_per_night = Column(Float, nullable=False)
    star_rating = Column(Float)
    has_pool = Column(Boolean, default=False)
    is_family_friendly = Column(Boolean, default=False)
    image_url = Column(String(500))

    agency = relationship("Agency", back_populates="hotels")
    bundles = relationship("Bundle", back_populates="hotel")
    bookings = relationship("Booking", back_populates="hotel")


class Flight(Base):
    """Cache table for flight data."""
    __tablename__ = "flights"

    flight_id = Column(Integer, primary_key=True, index=True)
    external_flight_id = Column(String(255))
    departure_city = Column(String(255))
    arrival_city = Column(String(255))
    departure_date = Column(String(50))
    return_date = Column(String(50))
    price = Column(Float, nullable=False)
    adults = Column(Integer, default=2)
    children = Column(Integer, default=0)
    airline = Column(String(255))

    bookings = relationship("Booking", back_populates="flight")


class Activity(Base):
    """Cache table for attraction/activity data."""
    __tablename__ = "activities"

    activity_id = Column(Integer, primary_key=True, index=True)
    external_activity_id = Column(String(255))
    name = Column(String(255), nullable=False)
    age_group = Column(String(100))
    price = Column(Float, nullable=False)
    restrictions = Column(Text)
    is_theme_park = Column(Boolean, default=False)
    city = Column(String(255))
    description = Column(Text)
    image_url = Column(String(500))

    bundles = relationship("Bundle", back_populates="activity")


class Bundle(Base):
    """Hotel + Activity package (supports theme park ticket bundles)."""
    __tablename__ = "bundles"

    bundle_id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.hotel_id"))
    activity_id = Column(Integer, ForeignKey("activities.activity_id"))
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    includes_theme_park = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)

    hotel = relationship("Hotel", back_populates="bundles")
    activity = relationship("Activity", back_populates="bundles")
    agency = relationship("Agency", back_populates="bundles")
    bookings = relationship("Booking", back_populates="bundle")


class Booking(Base):
    """Transaction record with Pending → Confirmed → Cancelled lifecycle."""
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
    children_ages = Column(String(100))
    status = Column(String(50), default="Pending")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="bookings")
    agency = relationship("Agency", back_populates="bookings")
    hotel = relationship("Hotel", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")
    bundle = relationship("Bundle", back_populates="bookings")
