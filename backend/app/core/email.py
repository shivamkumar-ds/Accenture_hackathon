"""
Contact form email delivery — Resend (transactional email API), Contact
Form Backend feature.

Two independent sends per submission, both best-effort and never allowed
to affect whether the submission itself persisted (see
app/services/contact_service.py, which calls these only *after* the
ContactSubmission row has already committed -- "persist first, email
best-effort," per the governing spec):

  - send_contact_notification(): tells BidOps a new message arrived, at
    settings.contact_notification_email. Reply-To is set to the visitor's
    own work_email, so a human at BidOps can just hit "Reply" in their
    own mail client -- the visitor is never used as the *From* address
    (that would be sender spoofing; most receiving mail servers would
    flag or reject it outright since BidOps doesn't control the
    visitor's domain's SPF/DKIM records). From is always
    settings.contact_sender_email, a address BidOps has verified with
    Resend.
  - send_contact_confirmation(): a minimal "we received your message"
    auto-reply back to the visitor.

Plain-text bodies only, deliberately -- every field interpolated into
these messages (name, company, message text, ...) is untrusted visitor
input. An HTML body would need each field HTML-escaped to avoid
injecting markup/links into what BidOps staff read in their inbox; plain
text sidesteps that whole class of problem for a form this simple, at no
real cost to readability.

Local development / test posture: if RESEND_API_KEY or
CONTACT_SENDER_EMAIL is not configured, both functions return a FAILED
EmailResult immediately, with a clear "not configured" reason, and log a
warning -- they never raise, and never silently pretend to have sent
something. This is what lets local dev and the test suite run with zero
real Resend credentials while still exercising every code path around
both calls.

`_send_email()` is the single seam that actually talks to the `resend`
SDK -- tests monkeypatch this one function, never the resend package
itself, matching the pattern already established for auth_service.
_verify_google_id_token() (Phase 2: Google Authentication).
"""

import logging
import uuid
from dataclasses import dataclass

import resend

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    sent: bool
    error: str | None = None


def _send_email(
    *, to: str, from_email: str, subject: str, text: str, reply_to: str | None = None
) -> None:
    """
    The one function that actually calls Resend. Raises on any failure
    (whatever the `resend` SDK itself raises for a network error or a
    non-2xx API response) -- callers catch broadly around this single
    call site and turn a failure into an EmailResult, so a Resend outage
    or misconfiguration never becomes an unhandled exception or bubbles
    up as a 500 to a visitor who successfully submitted the form.
    """
    resend.api_key = get_settings().resend_api_key
    params: dict = {
        "from": from_email,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if reply_to:
        params["reply_to"] = [reply_to]
    resend.Emails.send(params)


def _not_configured_result() -> EmailResult:
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("RESEND_API_KEY", settings.resend_api_key),
            ("CONTACT_SENDER_EMAIL", settings.contact_sender_email),
        )
        if not value
    ]
    reason = f"Resend is not configured (missing: {', '.join(missing)})."
    return EmailResult(sent=False, error=reason)


def send_contact_notification(
    *,
    submission_id: uuid.UUID,
    full_name: str,
    work_email: str,
    company_name: str | None,
    job_title: str | None,
    phone: str | None,
    subject: str,
    message: str,
) -> EmailResult:
    """Notifies BidOps's own inbox of a new contact form submission."""
    settings = get_settings()
    if not settings.resend_api_key or not settings.contact_sender_email:
        result = _not_configured_result()
        logger.warning(
            "Contact notification email skipped for submission %s -- %s",
            submission_id,
            result.error,
        )
        return result

    body = "\n".join(
        [
            f"New contact form submission ({submission_id})",
            "",
            f"Name: {full_name}",
            f"Email: {work_email}",
            f"Company: {company_name or '—'}",
            f"Job Title: {job_title or '—'}",
            f"Phone: {phone or '—'}",
            f"Subject: {subject}",
            "",
            "Message:",
            message,
        ]
    )
    try:
        _send_email(
            to=settings.contact_notification_email,
            from_email=settings.contact_sender_email,
            subject=f"[BidOps Contact] {subject}",
            text=body,
            reply_to=work_email,
        )
    except Exception as exc:  # noqa: BLE001 — provider/network failure, deliberately broad; see module docstring
        # Never log the full message body — it's untrusted visitor
        # content, potentially including personal data not relevant to a
        # delivery-failure log line. submission_id is enough to look the
        # row up if follow-up is needed.
        logger.warning(
            "Contact notification email failed for submission %s: %s", submission_id, exc
        )
        return EmailResult(sent=False, error=str(exc))

    logger.info("Contact notification email sent for submission %s.", submission_id)
    return EmailResult(sent=True)


def send_contact_confirmation(
    *, submission_id: uuid.UUID, full_name: str, work_email: str
) -> EmailResult:
    """Best-effort "we received your message" auto-reply to the visitor."""
    settings = get_settings()
    if not settings.resend_api_key or not settings.contact_sender_email:
        result = _not_configured_result()
        logger.warning(
            "Contact confirmation email skipped for submission %s -- %s",
            submission_id,
            result.error,
        )
        return result

    first_name = full_name.strip().split(" ")[0] if full_name.strip() else "there"
    body = "\n".join(
        [
            f"Hi {first_name},",
            "",
            "Thanks for reaching out to BidOps. We've received your message and "
            "a member of our team will get back to you shortly.",
            "",
            "— The BidOps Team",
        ]
    )
    try:
        _send_email(
            to=work_email,
            from_email=settings.contact_sender_email,
            subject="We've received your message — BidOps",
            text=body,
        )
    except Exception as exc:  # noqa: BLE001 — provider/network failure, deliberately broad; see module docstring
        logger.warning(
            "Contact confirmation email failed for submission %s: %s", submission_id, exc
        )
        return EmailResult(sent=False, error=str(exc))

    logger.info("Contact confirmation email sent for submission %s.", submission_id)
    return EmailResult(sent=True)
