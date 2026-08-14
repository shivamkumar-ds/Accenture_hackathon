"""
HTTP-layer regression coverage for POST /api/v1/contact (Contact Form
Backend feature) -- the concerns that only exist at the router/FastAPI
level and can't be exercised by calling contact_service directly:
no-authentication-required, the honeypot producing an identical-shaped
response, and the endpoint's own rate limit.

Uses a real FastAPI TestClient against the actual app, with `get_db`
overridden to an in-memory SQLite session (same fixture shape as every
other test in this suite) and app.core.email's two send functions
monkeypatched so no real Resend call is ever attempted. slowapi's
`limiter` is a process-wide singleton (app.core.rate_limit.limiter) --
`limiter.reset()` is called before each test in this file so one test's
requests never count against another's budget.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core import email
from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models import ContactSubmission


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ContactSubmission.__table__])
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(email, "send_contact_notification", lambda **kw: email.EmailResult(sent=True))
    monkeypatch.setattr(email, "send_contact_confirmation", lambda **kw: email.EmailResult(sent=True))
    # The app's real startup lifespan runs the migration guard against
    # settings.database_url (real Postgres) -- irrelevant to what these
    # tests exercise (the contact router against an in-memory SQLite
    # session, wired in via the get_db override above), and there is no
    # Postgres available in this test environment. Disabled the same way
    # any one-off script that intentionally runs before migrating would.
    #
    # Patched on app.main's own already-imported `settings` object
    # directly (not a fresh get_settings() call) -- some other test
    # modules in this suite call get_settings.cache_clear() without
    # restoring it, which would otherwise make a new call to
    # get_settings() here return a *different* Settings instance than
    # the one main.py's lifespan actually reads, silently no-op'ing this
    # patch depending on test run order.
    monkeypatch.setattr(main_module.settings, "migration_guard_enabled", False)

    limiter.reset()
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    limiter.reset()


def _valid_body(**overrides):
    body = dict(
        full_name="Priya Sharma",
        work_email="priya@acme.example",
        company_name="Acme Infrastructure",
        job_title="Procurement Lead",
        phone="+91 98765 43210",
        subject="General Inquiry",
        message="We'd like to learn more about BidOps.",
    )
    body.update(overrides)
    return body


def test_submit_contact_requires_no_authentication(client):
    """No Authorization header at all -- unlike every other mutating
    endpoint in this API, this must succeed."""
    res = client.post("/api/v1/contact", json=_valid_body())
    assert res.status_code == 201
    body = res.json()
    assert "id" in body and "created_at" in body


def test_submit_contact_is_independent_of_any_company(client):
    """No company header/token/scoping of any kind is involved."""
    res = client.post("/api/v1/contact", json=_valid_body())
    assert res.status_code == 201


def test_honeypot_field_returns_identical_shaped_success(client):
    res = client.post("/api/v1/contact", json=_valid_body(website="http://spammy.example"))
    assert res.status_code == 201
    body = res.json()
    assert "id" in body and "created_at" in body  # same shape as a real success


def test_missing_required_field_returns_422(client):
    body = _valid_body()
    del body["full_name"]
    res = client.post("/api/v1/contact", json=body)
    assert res.status_code == 422


def test_invalid_email_returns_422(client):
    res = client.post("/api/v1/contact", json=_valid_body(work_email="not-an-email"))
    assert res.status_code == 422


def test_rate_limit_blocks_the_sixth_request_in_an_hour(client):
    for _ in range(5):
        res = client.post("/api/v1/contact", json=_valid_body())
        assert res.status_code == 201

    res = client.post("/api/v1/contact", json=_valid_body())
    assert res.status_code == 429
