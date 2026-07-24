"""
Password hashing and JWT utilities.

bcrypt is used directly, not passlib — passlib has a known compatibility
break with recent bcrypt releases (it reads a bcrypt.__about__ attribute
that current bcrypt versions removed). Calling bcrypt directly avoids
that entirely and drops a dependency.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: uuid.UUID) -> str:
    """
    The token payload intentionally carries only the user id and expiry —
    not role or status. Authorization always re-fetches the user from the
    database (see app.api.deps.get_current_user), so a demoted or
    deactivated user's existing token stops granting access immediately,
    rather than remaining valid with stale permissions until it expires.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Raises jwt.PyJWTError (or a subclass) on invalid/expired tokens — callers handle it."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return uuid.UUID(payload["sub"])
