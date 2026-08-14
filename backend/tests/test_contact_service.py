"""
Regression coverage for contact_service.submit_contact_form() (Contact
Form Backend feature) -- the service-layer logic behind the public
Contact Us form: persistence, honest email status tracking, and the
honeypot short-circuit.

Never contacts real Resend -- every test monkeypatches
app.core.email.send_contact_notification / send_contact_confirmation,
the two seams the service calls, matching the pattern already
established for auth_service._verify_google_id_token (Phase 2). This is
deliberately one level higher than mocking `_send_email` directly: it
lets these tests assert on what the *service* does with a given email
outcome (status/error fields, that persistence never depends on it)
without also re-testing app/core/email.py's own internals here (that's
tests/test_contact_email.py's job).
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import email
from app.core.database import Base
from app.models import ContactSubmission
from app.models.enums import ContactEmailStatus
from app.schemas.contact import ContactRequest
from app.services import contact_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ContactSubmission.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _payload(**overrides) -> ContactRequest:
    defaults = dict(
        full_name="Priya Sharma",
        work_email="priya@acme.example",
        company_name="Acme Infrastructure",
        job_title="Procurement Lead",
        phone="+91 98765 43210",
        subject="General Inquiry",
        message="We'd like to learn more about BidOps.",
    )
    defaults.update(overrides)
    return ContactRequest(**defaults)


def _stub_both_emails(monkeypatch, *, notification_sent=True, confirmation_sent=True):
    monkeypatch.setattr(
        email, "send_contact_notification",
        lambda **kw: email.EmailResult(sent=notification_sent, error=None if notification_sent else "boom"),
    )
    monkeypatch.setattr(
        email, "send_contact_confirmation",
        lambda **kw: email.EmailResult(sent=confirmation_sent, error=None if confirmation_sent else "boom"),
    )


def test_valid_submission_is_persisted_with_all_fields(db, monkeypatch):
    _stub_both_emails(monkeypatch)
    submission = contact_service.submit_contact_form(db, _payload())

    assert submission is not None
    assert submission.id is not None
    assert submission.full_name == "Priya Sharma"
    assert submission.work_email == "priya@acme.example"
    assert submission.company_name == "Acme Infrastructure"
    assert submission.subject == "General Inquiry"
    assert submission.message == "We'd like to learn more about BidOps."


def test_submission_row_actually_exists_in_the_database(db, monkeypatch):
    """Not just that the function returns an object -- that it's really
    durable, independently re-queryable by id (the actual persistence
    guarantee the spec cares about)."""
    _stub_both_emails(monkeypatch)
    submission = contact_service.submit_contact_form(db, _payload())

    reloaded = db.query(ContactSubmission).filter_by(id=submission.id).one()
    assert reloaded.work_email == "priya@acme.example"


def test_optional_fields_may_be_omitted(db, monkeypatch):
    _stub_both_emails(monkeypatch)
    submission = contact_service.submit_contact_form(
        db, _payload(company_name=None, job_title=None, phone=None)
    )
    assert submission.company_name is None
    assert submission.job_title is None
    assert submission.phone is None


def test_notification_email_success_recorded_honestly(db, monkeypatch):
    _stub_both_emails(monkeypatch, notification_sent=True)
    submission = contact_service.submit_contact_form(db, _payload())
    assert submission.notification_status == ContactEmailStatus.SENT
    assert submission.notification_error is None


def test_notification_email_provider_failure_does_not_lose_the_submission(db, monkeypatch):
    """The critical durability guarantee from the governing spec: an
    email provider outage must never cause a real submission to be lost
    or falsely reported as failed."""
    _stub_both_emails(monkeypatch, notification_sent=False)
    submission = contact_service.submit_contact_form(db, _payload())

    assert submission is not None  # the row still exists
    assert submission.notification_status == ContactEmailStatus.FAILED
    assert submission.notification_error == "boom"
    # And it's still durably queryable afterwards -- not rolled back.
    assert db.query(ContactSubmission).filter_by(id=submission.id).count() == 1


def test_confirmation_email_status_tracked_independently_of_notification(db, monkeypatch):
    """Two separate Resend calls -- one can fail while the other
    succeeds, and the model must reflect that distinction rather than
    collapsing both into one status."""
    _stub_both_emails(monkeypatch, notification_sent=True, confirmation_sent=False)
    submission = contact_service.submit_contact_form(db, _payload())

    assert submission.notification_status == ContactEmailStatus.SENT
    assert submission.confirmation_status == ContactEmailStatus.FAILED
    assert submission.confirmation_error == "boom"


def test_honeypot_field_discards_without_persisting_or_emailing(db, monkeypatch):
    notification_called = confirmation_called = False

    def _fail_if_called(**kw):
        nonlocal notification_called
        notification_called = True
        raise AssertionError("must not be called for a honeypot hit")

    def _fail_if_called_confirm(**kw):
        nonlocal confirmation_called
        confirmation_called = True
        raise AssertionError("must not be called for a honeypot hit")

    monkeypatch.setattr(email, "send_contact_notification", _fail_if_called)
    monkeypatch.setattr(email, "send_contact_confirmation", _fail_if_called_confirm)

    result = contact_service.submit_contact_form(db, _payload(website="http://spammy.example"))

    assert result is None
    assert not notification_called
    assert not confirmation_called
    assert db.query(ContactSubmission).count() == 0


def test_submission_has_no_company_or_user_dependency(db, monkeypatch):
    """This endpoint must work for a completely anonymous visitor -- no
    Company or User row exists anywhere in this test's database at all,
    and submission must still succeed."""
    _stub_both_emails(monkeypatch)
    submission = contact_service.submit_contact_form(db, _payload())
    assert submission is not None
    assert not hasattr(ContactSubmission, "company_id")


def test_pydantic_schema_rejects_missing_required_fields():
    with pytest.raises(Exception):
        ContactRequest(work_email="a@b.example", subject="x", message="hi")  # missing full_name


def test_pydantic_schema_rejects_invalid_email():
    with pytest.raises(Exception):
        _payload(work_email="not-an-email")


def test_pydantic_schema_rejects_oversized_message():
    with pytest.raises(Exception):
        _payload(message="x" * 5001)


def test_pydantic_schema_rejects_oversized_name():
    with pytest.raises(Exception):
        _payload(full_name="x" * 201)
