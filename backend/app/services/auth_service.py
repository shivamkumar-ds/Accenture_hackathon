"""Auth service — registration (Company + first Administrator, atomically) and login."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import Company, User
from app.models.enums import UserRole, UserStatus
from app.schemas.auth import RegisterRequest
from app.services.exceptions import AuthenticationError, ConflictError
from app.services.user_service import get_user_by_email


def register(db: Session, data: RegisterRequest) -> tuple[str, User]:
    """
    Creates a new Company and its first Administrator user atomically —
    both succeed together or neither is persisted.
    """
    company = Company(
        name=data.company_name,
        industry=data.industry,
        registration_number=data.registration_number,
        country=data.country,
    )
    db.add(company)
    try:
        db.flush()  # assigns company.id without committing yet
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"A company with registration number '{data.registration_number}' already exists."
        ) from exc

    user = User(
        company_id=company.id,
        name=data.admin_name,
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        role=UserRole.ADMINISTRATOR,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"A user with email '{data.admin_email}' already exists.") from exc
    db.refresh(user)

    token = create_access_token(user.id)
    return token, user


def login(db: Session, email: str, password: str) -> tuple[str, User]:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")
    if user.status != UserStatus.ACTIVE:
        # Same message as a bad password — don't reveal account state to an unauthenticated caller.
        raise AuthenticationError("Invalid email or password.")
    token = create_access_token(user.id)
    return token, user
