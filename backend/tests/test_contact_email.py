"""
Regression coverage for app/core/email.py (Contact Form Backend feature)
-- the Resend integration itself.

Never contacts real Resend -- every test monkeypatches
app.core.email._send_email(), the one seam that actually calls the
`resend` SDK, matching the pattern already established for
auth_service._verify_google_id_token (Phase 2: Google Authentication).
"""

import uuid

import pytest

from app.core import email
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _configured_resend(monkeypatch):
    """Most tests here want a fully-configured Resend -- only the two
    "not configured" tests explicitly opt out of this fixture's effect
    by overriding the settings again themselves."""
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    monkeypatch.setattr(settings, "contact_sender_email", "no-reply@bidops.example")
    monkeypatch.setattr(settings, "contact_notification_email", "inbox@bidops.example")
    yield


def test_notification_email_success(monkeypatch):
    sent_calls = []
    monkeypatch.setattr(email, "_send_email", lambda **kw: sent_calls.append(kw))

    result = email.send_contact_notification(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
        company_name="Acme", job_title="Lead", phone="+91...", subject="Sales", message="Hello",
    )

    assert result.sent is True
    assert result.error is None
    assert len(sent_calls) == 1
    call = sent_calls[0]
    assert call["to"] == "inbox@bidops.example"
    assert call["from_email"] == "no-reply@bidops.example"
    # Reply-To must be the visitor, never used as the From address --
    # the whole point of this design (see module docstring: sender
    # spoofing would get flagged/rejected by receiving mail servers).
    assert call["reply_to"] == "priya@acme.example"
    assert "Hello" in call["text"]


def test_confirmation_email_success(monkeypatch):
    sent_calls = []
    monkeypatch.setattr(email, "_send_email", lambda **kw: sent_calls.append(kw))

    result = email.send_contact_confirmation(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
    )

    assert result.sent is True
    call = sent_calls[0]
    assert call["to"] == "priya@acme.example"
    assert call["from_email"] == "no-reply@bidops.example"


def test_notification_email_provider_failure_is_reported_not_raised(monkeypatch):
    def _boom(**kw):
        raise RuntimeError("Resend API unreachable")

    monkeypatch.setattr(email, "_send_email", _boom)

    result = email.send_contact_notification(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
        company_name=None, job_title=None, phone=None, subject="Sales", message="Hello",
    )

    assert result.sent is False
    assert "Resend API unreachable" in result.error


def test_confirmation_email_provider_failure_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(email, "_send_email", lambda **kw: (_ for _ in ()).throw(RuntimeError("down")))

    result = email.send_contact_confirmation(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
    )

    assert result.sent is False
    assert "down" in result.error


def test_notification_skipped_honestly_when_resend_not_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "contact_sender_email", "")
    called = []
    monkeypatch.setattr(email, "_send_email", lambda **kw: called.append(kw))

    result = email.send_contact_notification(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
        company_name=None, job_title=None, phone=None, subject="Sales", message="Hello",
    )

    assert result.sent is False
    assert "not configured" in result.error
    assert called == []  # never even attempts the call -- no exception needed to prove this


def test_confirmation_skipped_honestly_when_resend_not_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "")
    called = []
    monkeypatch.setattr(email, "_send_email", lambda **kw: called.append(kw))

    result = email.send_contact_confirmation(
        submission_id=uuid.uuid4(), full_name="Priya Sharma", work_email="priya@acme.example",
    )

    assert result.sent is False
    assert called == []
