"""Auth API — registration, login, and the current-user profile endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services import auth_service
from app.services.exceptions import AuthenticationError, ConflictError

router = APIRouter(prefix="/auth", tags=["auth"])


# 5/hour per IP (RC-2 finding H-2): registration is fully open by design —
# it's how a new company signs up at all — so this is the only thing
# standing between it and unlimited free account creation.
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token, user = auth_service.register(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


# 10/minute per IP — brute-force/credential-stuffing protection.
@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token, user = auth_service.login(db, payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/profile", response_model=UserRead)
def profile(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user
