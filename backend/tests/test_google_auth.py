"""
Regression coverage for Phase 2 (Google Authentication): auth_service.login_with_google().

Never contacts real Google infrastructure -- every test monkeypatches
auth_service._verify_google_id_token(), the one seam that wraps the
google-auth library call, exactly the same pattern used for LLM provider
seams elsewhere in this codebase. What's under test is BidOps' own logic
once a token has been verified: first-time linking by verified email,
google_sub-first lookup on subsequent logins, rejecting unknown accounts
(login/link only -- never creates a Company), rejecting an unverified
email, and inactive-account handling.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Company, User
from app.models.enums import AuthProvider, UserRole, UserStatus
from app.services import auth_service
from app.services.exceptions import AuthenticationError


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Company.__table__, User.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_local_user(db, email="admin@acme.example", status=UserStatus.ACTIVE):
    company = Company(id=uuid.uuid4(), name="Acme", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=email,
        password_hash="bcrypt-hash-not-relevant-here", role=UserRole.ADMINISTRATOR, status=status,
    )
    db.add(user)
    db.commit()
    return company, user


def test_first_google_login_links_existing_account_by_verified_email(db, monkeypatch):
    _company, user = _make_local_user(db)
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-123", "email": user.email, "email_verified": True},
    )

    token, logged_in_user = auth_service.login_with_google(db, "fake-token")

    assert token
    assert logged_in_user.id == user.id
    db.refresh(user)
    assert user.google_sub == "google-sub-123"
    assert user.auth_provider == AuthProvider.GOOGLE
    assert user.password_hash == "bcrypt-hash-not-relevant-here"  # existing password left untouched


def test_second_google_login_matches_by_sub_not_email_again(db, monkeypatch):
    _company, user = _make_local_user(db)
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-123", "email": user.email, "email_verified": True},
    )
    auth_service.login_with_google(db, "fake-token")  # first login: links

    # Second login: even if the claims now carry a *different* (unverified)
    # email, the existing google_sub link must still resolve to the same
    # user -- proving the lookup is sub-first, not re-derived from email
    # every time.
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-123", "email": "changed@elsewhere.example", "email_verified": False},
    )
    token, logged_in_user = auth_service.login_with_google(db, "fake-token-2")

    assert token
    assert logged_in_user.id == user.id


def test_google_login_never_creates_a_company_for_an_unknown_email(db, monkeypatch):
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-999", "email": "stranger@nowhere.example", "email_verified": True},
    )

    with pytest.raises(AuthenticationError):
        auth_service.login_with_google(db, "fake-token")

    assert db.query(Company).count() == 0
    assert db.query(User).count() == 0


def test_google_login_rejects_unverified_email(db, monkeypatch):
    _company, user = _make_local_user(db)
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-123", "email": user.email, "email_verified": False},
    )

    with pytest.raises(AuthenticationError):
        auth_service.login_with_google(db, "fake-token")

    db.refresh(user)
    assert user.google_sub is None  # never linked on an unverified claim


def test_google_login_rejects_inactive_account(db, monkeypatch):
    _company, user = _make_local_user(db, status=UserStatus.INACTIVE)
    monkeypatch.setattr(
        auth_service, "_verify_google_id_token",
        lambda raw: {"sub": "google-sub-123", "email": user.email, "email_verified": True},
    )

    with pytest.raises(AuthenticationError):
        auth_service.login_with_google(db, "fake-token")


def test_password_login_on_a_google_only_account_fails_cleanly_not_crashing(db):
    """A GOOGLE-provider account has password_hash = None. Logging in with
    a password must be a clean AuthenticationError, not a crash from
    verify_password() being handed a None hash."""
    company = Company(id=uuid.uuid4(), name="Acme", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Google Only", email="google-only@acme.example",
        password_hash=None, auth_provider=AuthProvider.GOOGLE, google_sub="google-sub-555",
        role=UserRole.REVIEWER, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()

    with pytest.raises(AuthenticationError):
        auth_service.login(db, "google-only@acme.example", "any-password")
