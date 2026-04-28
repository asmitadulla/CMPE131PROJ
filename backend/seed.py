# =============================================================================
# seed.py
#
# Inserts sample Hotel, Activity, and Agency records into the database so
# that bundle creation (POST /api/v1/bundles/) has valid IDs to reference.
#
# Run once before testing bundles:
#   python seed.py
# =============================================================================

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Check if seed data already exists
if db.query(models.Agency).filter(models.Agency.domain == "familytravel.demo").first():
    print("Seed data already exists. Skipping.")
    db.close()
    exit()

# --- Agency ---
agency = models.Agency(
    name="Family Travel Co",
    domain="familytravel.demo",
    theme_settings={"primary_color": "#0066cc"},
    max_passengers=10,
    max_bundles_per_user=5,
)
db.add(agency)
db.flush()

# --- Hotel ---
hotel = models.Hotel(
    agency_id=agency.agency_id,
    external_hotel_id="booking-12345",
    name="Walt Disney World Swan Resort",
    city="Orlando",
    capacity=4,
    amenities=["Pool", "Kids Club", "Family Rooms", "Restaurant"],
    price_per_night=299.0,
    star_rating=4.0,
    has_pool=True,
    is_family_friendly=True,
    image_url="https://example.com/swan-resort.jpg",
)
db.add(hotel)
db.flush()

# --- Activity ---
activity = models.Activity(
    external_activity_id="booking-att-99999",
    name="Walt Disney World Resort Single Day Base Ticket",
    age_group="All ages",
    price=185.0,
    restrictions="Children under 3 free",
    is_theme_park=True,
    city="Orlando",
    description="Access to one Disney theme park per day.",
    image_url="https://example.com/disney-ticket.jpg",
)
db.add(activity)
db.flush()

db.commit()

print(f"Seed complete!")
print(f"  Agency ID  : {agency.agency_id}  (domain: {agency.domain})")
print(f"  Hotel ID   : {hotel.hotel_id}   ({hotel.name})")
print(f"  Activity ID: {activity.activity_id}  ({activity.name})")
print()
print("Use these IDs when calling POST /api/v1/bundles/")

db.close()
