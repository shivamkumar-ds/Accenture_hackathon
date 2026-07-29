"""
BidOps AI — Application entrypoint.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter

# Configured before anything else runs, so every logger created below
# (including the ones module-level `logger = logging.getLogger(__name__)`
# calls in other modules resolve to at import time) inherits the level and
# format set here.
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
logger.info("Starting %s (environment=%s)", settings.app_name, settings.app_env)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Enterprise Bid Decision Intelligence Platform",
    debug=settings.debug,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Phase 1.5 finding #3 — standard, low-cost hardening headers absent
    until now. CORS already restricts which origins can call this API
    (above); these headers restrict what a browser is allowed to do with
    the response once received: never sniff a response's content-type
    into something more dangerous than declared, never render this API
    inside a frame (there's no legitimate embedding use case), and always
    upgrade to HTTPS on repeat visits once actually served over it. HSTS
    is real only over HTTPS -- browsers ignore it over plain HTTP -- so it
    only fires outside local dev to avoid an inert header on every
    response during development."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if settings.app_env != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS (BidOps_Final Milestone 4). Env-driven allowlist rather than a
# single hardcoded origin, so the same code runs correctly across local
# dev, staging, and production without a source change per environment.
# ALLOWED_ORIGINS is a comma-separated list (see .env.example); defaults
# to the local Vite dev server so a fresh checkout works unmodified.
# Never a wildcard -- an explicit, reviewable origin list only, matching
# the project's own "never silently permissive" security posture.
allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (RC-2 audit finding H-2) — the limiter instance and its
# per-route limits live in app/core/rate_limit.py and each decorated route;
# this is just the app-level wiring slowapi requires: register the shared
# limiter, translate an exceeded limit into a proper 429 response, and add
# the middleware that attaches rate-limit headers to responses.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["infrastructure"])
def health_check() -> dict:
    """Unversioned infrastructure health check — not part of the business API."""
    return {"status": "ok", "environment": settings.app_env}
