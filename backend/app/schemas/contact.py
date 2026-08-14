"""Pydantic schemas for the public "Contact Us" form (Contact Form Backend)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    work_email: EmailStr
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)

    # Honeypot. A hidden input on the frontend (ContactSection.tsx) that
    # a real visitor never sees or fills, but many spam bots auto-fill
    # every input on a form. Left non-empty here means "very likely a
    # bot" -- the service layer discards the request without persisting
    # it or sending any email, and the router still returns a normal
    # 201 success so nothing about the response tips a bot off that it
    # was filtered rather than accepted. Never rendered as a visible
    # field, never validated beyond max_length (its content is never
    # used for anything except the emptiness check).
    website: str = Field(default="", max_length=200)


class ContactResponse(BaseModel):
    id: UUID
    created_at: datetime
