# =============================================================================
# routers/auth.py
#
# Handles all authentication and agency (tenant) registration.
#
# Endpoints:
#   POST /api/v1/auth/agency  — Register a new travel agency (tenant)
#   POST /api/v1/auth/signup  — Register a new user under an agency
#   POST /api/v1/auth/login   — Login and receive a JWT token
#
# Also exports get_current_user(), a reusable FastAPI dependency that other
# routers (e.g. bookings.py) use to protect their endpoints. It reads the
# Bearer token from the Authorization header, decodes it, and returns the
# matching User from the database.
#
# Passwords are hashed with bcrypt via passlib. Tokens are signed HS256 JWTs
# via python-jose and expire after 24 hours.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas import AgencyCreate, AgencyResponse, UserCreate, UserLogin, UserResponse, Token
from passlib.context import CryptContext
from jose import jwt, JWTError
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()  # tells FastAPI/Swagger to expect "Authorization: Bearer <token>"

SECRET_KEY = os.getenv("SECRET_KEY", "travel-saas-secret-2024")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def _make_token(user_id: int, agency_id: int) -> str:
    """
    Creates a signed JWT token containing the user's ID and agency ID.
    The token expires after TOKEN_EXPIRE_HOURS hours.
    The agency_id is embedded so protected routes can enforce tenant isolation
    without an extra database lookup.
    """
    payload = {
        "sub": str(user_id),    # "sub" is the standard JWT subject claim
        "agency_id": agency_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    FastAPI dependency used to protect routes that require authentication.
    Reads the Bearer token from the Authorization header, decodes and
    validates it, then fetches and returns the corresponding User row.

    Raises HTTP 401 if:
      - The token is missing, malformed, or expired
      - The user_id in the token doesn't match any user in the database

    Usage in a router:
        current_user: models.User = Depends(get_current_user)
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/agency", response_model=AgencyResponse, summary="Register a new travel agency (tenant)")
def create_agency(agency: AgencyCreate, db: Session = Depends(get_db)):
    """
    Creates a new tenant agency. Each agency gets its own isolated space —
    its users, bookings, and bundles are not visible to other agencies.
    Domain must be unique across all agencies.
    """
    if db.query(models.Agency).filter(models.Agency.domain == agency.domain).first():
        raise HTTPException(status_code=400, detail="Agency domain already registered")

    db_agency = models.Agency(
        name=agency.name,
        domain=agency.domain,
        theme_settings=agency.theme_settings,
    )
    db.add(db_agency)
    db.commit()
    db.refresh(db_agency)
    return db_agency


@router.post("/signup", response_model=Token, summary="Register a new user under an agency")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user scoped to a specific agency.
    Email uniqueness is enforced per-agency (not globally), so the same
    email address can belong to users in different tenants.
    Returns a JWT token on success so the client is immediately logged in.
    """
    # Confirm the agency exists before creating the user
    if not db.query(models.Agency).filter(models.Agency.agency_id == user.agency_id).first():
        raise HTTPException(status_code=404, detail="Agency not found")

    # Check email is not already taken within this specific agency
    if db.query(models.User).filter(
        models.User.email == user.email,
        models.User.agency_id == user.agency_id,
    ).first():
        raise HTTPException(status_code=400, detail="Email already registered in this agency")

    db_user = models.User(
        agency_id=user.agency_id,
        name=user.name,
        email=user.email,
        password_hash=pwd_context.hash(user.password),  # never store plain text passwords
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return Token(
        access_token=_make_token(db_user.user_id, db_user.agency_id),
        token_type="bearer",
        user=UserResponse.model_validate(db_user),
    )


@router.post("/login", response_model=Token, summary="Login and receive JWT")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates a user under a specific agency and returns a JWT token.
    Lookup is scoped by both email AND agency_id so users from different
    tenants with the same email don't collide.
    """
    user = db.query(models.User).filter(
        models.User.email == credentials.email,
        models.User.agency_id == credentials.agency_id,
    ).first()

    # Use a single error message for both "user not found" and "wrong password"
    # to avoid leaking whether an email exists in the system
    if not user or not pwd_context.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return Token(
        access_token=_make_token(user.user_id, user.agency_id),
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.get("/me", response_model=UserResponse, summary="Get current logged-in user")
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Returns the currently authenticated user based on the JWT token.
    Used by the frontend to keep the user logged in and load dashboard/tenant info.
    """
    return UserResponse.model_validate(current_user)
