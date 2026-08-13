"""
BidOps AI — database engine and session management.

Synchronous SQLAlchemy is used deliberately for M0: the current workload
(Company/User CRUD, capability records) doesn't need async I/O, and an
async engine now would be complexity without a present benefit. If
agent-level I/O (e.g. Qwen Cloud calls) needs async handling later,
that's a separate, deliberate decision made when it's actually needed.

Cloud SQL connectivity (Phase 3: GCP deployment) needs no code here at
all -- DATABASE_URL was already the single, fully env-driven source of
truth before this deployment work started. Cloud Run's standard pattern
is a Unix domain socket via the Cloud SQL Auth Proxy sidecar/connector,
which is just a different value for the same setting, e.g.:
  postgresql+psycopg2://USER:PASSWORD@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE
psycopg2 already understands that `?host=/path` form natively; nothing
in this module needs to know it's talking to Cloud SQL specifically.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
)

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
