"""
Contact form service — the public "Contact Us" form (Contact Form
Backend feature). Router -> Service -> Model, matching every other
module in this codebase; no FastAPI/HTTP concerns here.

Persist-first, email-best-effort -- the governing spec's core durability
requirement: the ContactSubmission row is created and committed before
either email is attempted. A failure in either send updates that same
row's own status/error fields and is logged; it never rolls back the
submission and never raises past this function. The only way this
function raises is a genuine database failure writing the row itself,
which is the one case where "the submission was not durably recorded"
is actually true -- and that's exactly what should surface as a 500 to
the caller instead of being swallowed.
"""

import logging

from sqlalchemy.orm import Session

from app.core import email
from app.models import ContactSubmission
from app.models.enums import ContactEmailStatus
from app.schemas.contact import ContactRequest

logger = logging.getLogger(__name__)


def submit_contact_form(db: Session, payload: ContactRequest) -> ContactSubmission | None:
    """
    Returns the persisted ContactSubmission, or None if this request was
    silently discarded as a honeypot hit (payload.website non-empty --
    see ContactRequest's docstring). The router returns an
    identical-shaped success response either way, so a bot filling the
    honeypot field gets no signal that anything different happened.
    """
    if payload.website:
        logger.info(
            "Contact form honeypot triggered (claimed name='%s') -- discarded, not persisted.",
            payload.full_name,
        )
        return None

    submission = ContactSubmission(
        full_name=payload.full_name.strip(),
        work_email=payload.work_email,
        company_name=(payload.company_name.strip() if payload.company_name else None),
        job_title=(payload.job_title.strip() if payload.job_title else None),
        phone=(payload.phone.strip() if payload.phone else None),
        subject=payload.subject.strip(),
        message=payload.message.strip(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    logger.info("Contact form submission %s persisted.", submission.id)

    # From here on, nothing is allowed to lose the fact that the
    # submission above already durably exists -- every step is
    # best-effort and self-contained in its own try/except.
    notification_result = email.send_contact_notification(
        submission_id=submission.id,
        full_name=submission.full_name,
        work_email=submission.work_email,
        company_name=submission.company_name,
        job_title=submission.job_title,
        phone=submission.phone,
        subject=submission.subject,
        message=submission.message,
    )
    submission.notification_status = (
        ContactEmailStatus.SENT if notification_result.sent else ContactEmailStatus.FAILED
    )
    submission.notification_error = notification_result.error

    confirmation_result = email.send_contact_confirmation(
        submission_id=submission.id,
        full_name=submission.full_name,
        work_email=submission.work_email,
    )
    submission.confirmation_status = (
        ContactEmailStatus.SENT if confirmation_result.sent else ContactEmailStatus.FAILED
    )
    submission.confirmation_error = confirmation_result.error

    db.commit()
    db.refresh(submission)
    return submission
