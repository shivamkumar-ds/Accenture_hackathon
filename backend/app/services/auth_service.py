"""Auth service — registration (Company + first Administrator, atomically) and login."""

import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Company, User
from app.models.enums import AuthProvider, UserRole, UserStatus
from app.schemas.auth import RegisterRequest
from app.services.exceptions import AuthenticationError, ConflictError
from app.services.user_service import get_user_by_email

logger = logging.getLogger(__name__)


def register(db: Session, data: RegisterRequest) -> tuple[str, User]:
    """
    Creates a new Company and its first Administrator user atomically —
    both succeed together or neither is persisted.
    """
    company = Company(
        name=data.company_name,
        industry=data.industry,
        registration_number=data.registration_number,
        country=data.country,
    )
    db.add(company)
    try:
        db.flush()  # assigns company.id without committing yet
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"A company with registration number '{data.registration_number}' already exists."
        ) from exc

    user = User(
        company_id=company.id,
        name=data.admin_name,
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        role=UserRole.ADMINISTRATOR,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Registration failed — email '%s' already in use.", data.admin_email)
        raise ConflictError(f"A user with email '{data.admin_email}' already exists.") from exc
    db.refresh(user)

    logger.info("New company registered: company_id=%s user_id=%s", company.id, user.id)
    token = create_access_token(user.id)
    return token, user


def login(db: Session, email: str, password: str) -> tuple[str, User]:
    user = get_user_by_email(db, email)
    # A GOOGLE-provider account has password_hash = None by design (Phase 2:
    # Google Authentication) -- guarded explicitly here rather than letting
    # verify_password() crash on a None hash, and reported as the exact
    # same generic "Invalid email or password" as a wrong password, not a
    # distinguishable error that would tell an unauthenticated caller which
    # accounts exist and how they authenticate.
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        # Logging the email (not the password) is safe -- it's a username,
        # not a secret -- and is exactly the signal you'd want for spotting
        # brute-force/credential-stuffing patterns later. The response
        # message to the caller stays identical either way (see below);
        # this log entry is server-side only.
        logger.warning("Failed login attempt for email '%s'.", email)
        raise AuthenticationError("Invalid email or password.")
    if user.status != UserStatus.ACTIVE:
        # Same message as a bad password — don't reveal account state to an unauthenticated caller.
        logger.warning("Login attempt for inactive user_id=%s.", user.id)
        raise AuthenticationError("Invalid email or password.")
    token = create_access_token(user.id)
    logger.info("User logged in: user_id=%s", user.id)
    return token, user


def _verify_google_id_token(raw_token: str) -> dict:
    """
    Isolated into its own function so tests can monkeypatch exactly this
    call instead of reaching into the google-auth library — the same
    seam pattern used throughout the agents layer for LLM calls.

    Verifies signature, expiry, issuer, and audience (must match
    settings.google_oauth_client_id) via Google's own library — this app
    never re-implements token verification itself. Any failure (forged
    signature, expired, wrong audience, malformed token) raises
    AuthenticationError with a single generic message; the caller must
    never learn *which* check failed, same principle as the identical
    password login not distinguishing "no such user" from "wrong password".
    """
    settings = get_settings()
    if not settings.google_oauth_client_id:
        # A configuration gap, not a caller error -- surfaced distinctly
        # in the log (ERROR, not the routine AuthenticationError path)
        # so it's caught by an operator, not mistaken for a user typing
        # their password wrong.
        logger.error("Google sign-in attempted but GOOGLE_OAUTH_CLIENT_ID is not configured.")
        raise AuthenticationError("Google sign-in is not available.")
    try:
        return google_id_token.verify_oauth2_token(
            raw_token, google_requests.Request(), settings.google_oauth_client_id
        )
    except Exception as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        raise AuthenticationError("Invalid Google sign-in token.") from exc


def login_with_google(db: Session, raw_id_token: str) -> tuple[str, User]:
    """
    Login/link only — this never creates a Company. A Google-authenticated
    person must already exist as a User (created either as the original
    registering Administrator via /auth/register, or added by their
    company's Administrator via POST /users) before Google sign-in works
    for them. See docs/BUG_BUCKET.md-adjacent design note in the Phase 2
    commit message for why: company creation stays the one deliberate,
    auditable act it already is, rather than gaining a second, ambiguous
    "sign in with Google to spin up a brand-new company" path the frozen
    spec never asked for.

    First Google login for a given account: matched by *verified* email
    to an existing local account, then permanently linked via google_sub.
    Every subsequent Google login for that person is matched by google_sub
    directly, not by email again -- so a later email change on the Google
    side can never silently re-point the link at a different account.
    """
    claims = _verify_google_id_token(raw_id_token)
    google_sub = claims["sub"]

    user = db.query(User).filter(User.google_sub == google_sub).one_or_none()

    if user is None:
        email = claims.get("email")
        if not email or not claims.get("email_verified"):
            raise AuthenticationError("This Google account has no verified email address.")

        user = get_user_by_email(db, email)
        if user is None:
            logger.warning("Google sign-in attempted for unrecognized email '%s'.", email)
            raise AuthenticationError(
                "No BidOps account found for this Google account. "
                "Ask your company administrator to add you first."
            )

        # First-time link. Existing password (if any) is left completely
        # untouched -- linking Google adds a second way in, it never
        # revokes the first.
        user.google_sub = google_sub
        user.auth_provider = AuthProvider.GOOGLE
        db.commit()
        db.refresh(user)
        logger.info("Google account linked: user_id=%s", user.id)

    if user.status != UserStatus.ACTIVE:
        logger.warning("Google sign-in attempt for inactive user_id=%s.", user.id)
        raise AuthenticationError("This account is inactive.")

    token = create_access_token(user.id)
    logger.info("User logged in via Google: user_id=%s", user.id)
    return token, user
