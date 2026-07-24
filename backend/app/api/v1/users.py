"""
Users API.

POST is Administrator-only — adds a user to the admin's own company.
GET requires any authenticated user, and is scoped to their own company
(never returns another company's users, regardless of role).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_administrator
from app.core.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserRead
from app.services import user_service
from app.services.exceptions import ConflictError

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    admin: User = Depends(require_administrator),
    db: Session = Depends(get_db),
) -> UserRead:
    try:
        return user_service.create_user(
            db, admin.company_id, payload.name, payload.email, payload.password, payload.role
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    return user_service.list_users_by_company(db, current_user.company_id)
