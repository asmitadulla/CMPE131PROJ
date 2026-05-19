# =============================================================================
# main.py
#
# Entry point for the Travel Agent SaaS Platform API.
# Creates the FastAPI application, registers all middleware, and mounts all
# routers under the /api/v1 prefix.
#
# To run locally:
#   uvicorn main:app --reload
#
# Swagger UI (interactive docs) available at:
#   http://localhost:8000/docs
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from middleware.tenant import TenantMiddleware
from routers import auth, hotels, flights, attractions, bookings, bundles, tenants, recommendations

# Create all database tables on startup if they don't already exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Travel Agent SaaS Platform",
    description=(
        "Multi-tenant travel booking platform — Scenario #7: The Family Vacationist.\n\n"
        "Supports multi-passenger search (adults + children), family-friendly hotel filters "
        "(pool, amenities), bundle filtering (hotel + theme park tickets), and full booking "
        "lifecycle management (Pending → Confirmed → Cancelled).\n\n"
        "Pass `X-Agency-ID` header on all non-auth requests for tenant isolation."
    ),
    version="1.0.0",
)

# Allow all origins so the Vue.js frontend can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extracts X-Agency-ID header and attaches it to request.state for tenant isolation
app.add_middleware(TenantMiddleware)

# Register all routers — each group of endpoints lives in its own file
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(hotels.router, prefix="/api/v1/hotels", tags=["Hotels"])
app.include_router(flights.router, prefix="/api/v1/flights", tags=["Flights"])
app.include_router(attractions.router, prefix="/api/v1/attractions", tags=["Attractions"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
app.include_router(bundles.router, prefix="/api/v1/bundles", tags=["Bundles"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])


@app.get("/", tags=["Health"])
def root():
    # Simple health check — confirms the server is running
    return {"status": "running", "project": "Travel Agent SaaS Platform", "docs": "/docs"}
