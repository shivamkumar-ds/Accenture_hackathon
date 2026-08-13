"""Company and User — 05_Database_Design.md."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AuthProvider, UserRole, UserStatus
from app.models.mixins import UUIDPrimaryKeyMixin


class Company(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    registration_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="company")


class User(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "users"

    # index=True: list_users() and every RBAC check filter by company_id
    # (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Phase 2 (Google Authentication): nullable now -- a GOOGLE-provider
    # account genuinely has no password, ever. Never populated with a
    # random/unusable placeholder hash; NULL here is the real, queryable
    # fact "this account cannot log in with a password."
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # auth_provider default LOCAL preserves every existing account's
    # behavior unchanged. google_sub (the stable, unique Google account
    # identifier -- "sub" claim from the verified ID token) is the actual
    # link once a LOCAL account signs in with Google for the first time;
    # unique + nullable so at most one User row can ever claim a given
    # Google account, while every account that has never used Google stays
    # NULL. Looked up directly (not resolved via email) on every Google
    # login after the first, so a later email change on the Google side
    # can't silently sever or hijack the link.
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider"), nullable=False, default=AuthProvider.LOCAL
    )
    google_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="users")
