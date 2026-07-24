"""User service — business logic for User entities."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole, UserStatus
from app.services.exceptions import ConflictError, NotFoundError


def create_user(
    db: Session,
    company_id: uuid.UUID,
    name: str,
    email: str,
    password: str,
    role: UserRole,
) -> User:
    user = User(
        company_id=company_id,
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"A user with email '{email}' already exists.") from exc
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User '{user_id}' not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).one_or_none()


def list_users_by_company(db: Session, company_id: uuid.UUID) -> list[User]:
    return db.query(User).filter(User.company_id == company_id).order_by(User.created_at).all()
