"""
ContactSubmission — the public landing page's "Contact Us" form
(Contact Form Backend feature; see docs/BUG_BUCKET.md's contact-form-gap
discussion and the "Decision — Proceed With Contact Form Backend" spec
this implements).

Deliberately outside the multi-tenant Company/User graph: a visitor
submitting this form is, by definition, not yet a BidOps customer --
there is no company_id to scope this to, and it must work for a
completely anonymous, unauthenticated visitor. This is the one table in
the schema that is intentionally not company-scoped.

The row is the durable record of "a visitor submitted this" -- committed
before either email is attempted, and never rolled back because an email
later fails. notification_status/confirmation_status/*_error exist so
that fact (which email, if any, actually went out) is honestly queryable
after the fact, exactly like DocumentProcessingStatus tracks a document's
own async pipeline state elsewhere in this schema. This is not an inbox
or a CRM -- no read/reply/assignment state is modelled, deliberately
(explicitly out of scope per the governing spec).
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ContactEmailStatus
from app.models.mixins import UUIDPrimaryKeyMixin


class ContactSubmission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "contact_submissions"

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    # Not EmailStr at the model layer (that's a Pydantic/API-schema
    # concern, validated in ContactRequest) -- the DB column just stores
    # whatever validated value the schema layer already accepted.
    work_email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    # Free text, matching the frontend's existing <Select> options
    # ("General Inquiry", "Request a Demo", ...) -- not an enum, since
    # this is just a display/routing hint a human reads, not a value
    # anything in the backend branches logic on.
    subject: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # The notification to BidOps's own inbox -- the operationally
    # important one; a visitor's Reply-To is set to their own work_email
    # on this message (see app/core/email.py).
    notification_status: Mapped[ContactEmailStatus] = mapped_column(
        Enum(ContactEmailStatus, name="contact_email_status"),
        default=ContactEmailStatus.PENDING,
        nullable=False,
    )
    notification_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The best-effort "we received your message" auto-reply sent back to
    # the visitor. Tracked separately from notification_status because
    # they are two independent Resend API calls -- one can succeed while
    # the other fails, and collapsing them into one field would hide that.
    confirmation_status: Mapped[ContactEmailStatus] = mapped_column(
        Enum(ContactEmailStatus, name="contact_email_status"),
        default=ContactEmailStatus.PENDING,
        nullable=False,
    )
    confirmation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
