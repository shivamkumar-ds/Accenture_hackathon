"""Pydantic schemas for authentication — login, registration, tokens."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """
    Creates a brand-new Company and its first Administrator together.
    This is the only endpoint that creates a company from nothing —
    POST /api/v1/users (Administrator-only) adds further users to a
    company that already exists.
    """

    # Company fields
    company_name: str
    industry: str | None = None
    registration_number: str
    country: str | None = None

    # First administrator's fields
    admin_name: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
