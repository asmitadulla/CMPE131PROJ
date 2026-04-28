from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts X-Agency-ID header from every request and attaches it to
    request.state.agency_id for downstream tenant isolation.
    Auth and docs routes are exempt.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/api/auth"):
            request.state.agency_id = None
            return await call_next(request)

        agency_id_header = request.headers.get("X-Agency-ID")
        if agency_id_header:
            try:
                request.state.agency_id = int(agency_id_header)
            except ValueError:
                request.state.agency_id = None
        else:
            request.state.agency_id = None

        return await call_next(request)
