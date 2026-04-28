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
bearer_scheme = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "travel-saas-secret-2024")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def _make_token(user_id: int, agency_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "agency_id": agency_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Dependency that verifies the JWT and returns the authenticated user."""
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
    """Create a new tenant agency. Each agency is fully isolated."""
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
    Register a user scoped to a specific agency. Email uniqueness is enforced
    per-agency so the same email can exist in different tenants.
    """
    if not db.query(models.Agency).filter(models.Agency.agency_id == user.agency_id).first():
        raise HTTPException(status_code=404, detail="Agency not found")

    if db.query(models.User).filter(
        models.User.email == user.email,
        models.User.agency_id == user.agency_id,
    ).first():
        raise HTTPException(status_code=400, detail="Email already registered in this agency")

    db_user = models.User(
        agency_id=user.agency_id,
        name=user.name,
        email=user.email,
        password_hash=pwd_context.hash(user.password),
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
    user = db.query(models.User).filter(
        models.User.email == credentials.email,
        models.User.agency_id == credentials.agency_id,
    ).first()

    if not user or not pwd_context.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return Token(
        access_token=_make_token(user.user_id, user.agency_id),
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
