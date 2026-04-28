# =============================================================================
# middleware/tenant.py
#
# Tenant isolation middleware for the multi-tenant SaaS architecture.
#
# Every incoming request (except auth and docs routes) is expected to include
# an "X-Agency-ID" header identifying which travel agency the request belongs
# to. This middleware reads that header and stores the value on request.state
# so any router or service downstream can access it without re-reading headers.
#
# This is how the platform separates data between tenants:
#   - Agency A's users can only see Agency A's bookings
#   - Agency B's users can only see Agency B's bookings
#   - The agency_id is used as a filter on all DB queries in the routers
# =============================================================================

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# These paths don't belong to any tenant, so no X-Agency-ID is needed
EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Runs before every request handler. Reads the X-Agency-ID header and
    attaches its integer value to request.state.agency_id.

    If the header is missing or invalid, agency_id is set to None.
    Individual routes decide whether to enforce it or not.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip tenant resolution for public/docs/auth paths
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/api/v1/auth"):
            request.state.agency_id = None
            return await call_next(request)

        agency_id_header = request.headers.get("X-Agency-ID")
        if agency_id_header:
            try:
                # Convert header string to int — invalid values are treated as None
                request.state.agency_id = int(agency_id_header)
            except ValueError:
                request.state.agency_id = None
        else:
            request.state.agency_id = None

        return await call_next(request)
