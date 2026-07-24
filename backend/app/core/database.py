"""
BidOps AI — database engine and session management.

Synchronous SQLAlchemy is used deliberately for M0: the current workload
(Company/User CRUD, capability records) doesn't need async I/O, and an
async engine now would be complexity without a present benefit. If
agent-level I/O (e.g. Qwen Cloud calls) needs async handling later,
that's a separate, deliberate decision made when it's actually needed.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models (populated starting with the schema step)."""

    pass


def get_db() -> Session:
    """FastAPI dependency — yields a request-scoped database session, closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
