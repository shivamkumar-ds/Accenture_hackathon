"""Pydantic schemas for User."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole, UserStatus


class UserCreate(BaseModel):
    """Used by POST /api/v1/users — an Administrator adding a user to their own company."""

    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime
