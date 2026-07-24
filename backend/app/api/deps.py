"""
Shared API-layer dependencies — authentication and RBAC.

Kept in the API layer, not services, since they deal with an HTTP-specific
concern (the Authorization header) even though they call into the User
model for the actual lookup.
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole, UserStatus

# auto_error=False: by default, HTTPBearer raises its own 403 "Not
# authenticated" when the Authorization header is entirely missing —
# semantically wrong (401 means "authenticate"; 403 means "you did,
# but you're not allowed") and inconsistent with the 401 this same
# dependency returns for a present-but-invalid token. Disabling
# auto_error and handling the missing-header case explicitly below
# makes both cases return 401 uniformly.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict authentication — 401 for a missing, invalid, or expired
    token, or for a valid token belonging to a user who no longer exists
    or is inactive.

    Status is re-checked from the database on every request rather than
    trusted from the token, so deactivating a user takes effect
    immediately rather than only once their existing token expires.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception

    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_exception
    return user


def require_administrator(current_user: User = Depends(get_current_user)) -> User:
    """Authorization on top of authentication — the caller must specifically be an Administrator."""
    if current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the Administrator role.",
        )
    return current_user


def require_approver(current_user: User = Depends(get_current_user)) -> User:
    """
    Authorization for mission approval decisions. Executive is the
    intended production approver (per the PRD's role definitions);
    Administrator is also allowed so a newly registered company can
    complete the full workflow without first creating a separate
    Executive user — a deliberate bootstrap/MVP allowance, not an
    oversight.
    """
    if current_user.role not in (UserRole.EXECUTIVE, UserRole.ADMINISTRATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the Executive or Administrator role.",
        )
    return current_user
