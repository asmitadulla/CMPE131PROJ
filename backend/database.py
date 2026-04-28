# =============================================================================
# database.py
#
# Sets up the SQLAlchemy database connection and session for the app.
# Reads the DATABASE_URL from the .env file. Defaults to SQLite for local
# development, but can be switched to MySQL or PostgreSQL by changing
# DATABASE_URL in the .env file (e.g. mysql+pymysql://user:pass@host/db).
#
# Exports:
#   - engine       : the SQLAlchemy engine (used by models.py to create tables)
#   - SessionLocal : factory for creating DB sessions
#   - Base         : base class that all models inherit from
#   - get_db()     : FastAPI dependency that provides a DB session per request
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_saas.db")

# check_same_thread is SQLite-only — required because FastAPI handles requests
# across multiple threads and SQLite would otherwise raise an error
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that opens a database session for a single request
    and guarantees it is closed when the request finishes, even if an
    exception is raised.

    Usage in a router:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
