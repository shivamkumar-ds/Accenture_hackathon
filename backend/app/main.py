"""
BidOps AI — Application entrypoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import configure_logging
from app.core.migration_guard import MigrationOutOfDateError, check_migrations_current
from app.core.rate_limit import limiter

# Configured before anything else runs, so every logger created below
# (including the ones module-level `logger = logging.getLogger(__name__)`
# calls in other modules resolve to at import time) inherits the level and
# format set here.
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
logger.info("Starting %s (environment=%s)", settings.app_name, settings.app_env)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Migration safety system (docs/BUG_BUCKET.md Bug #001) -- runs before
    # the app accepts a single request. On a mismatch this either raises
    # (aborting startup outright, uvicorn exits non-zero) or logs and
    # continues, per migration_guard_fail_on_mismatch -- see config.py for
    # why the default is "fail" in every environment, including production.
    if settings.migration_guard_enabled:
        try:
            check_migrations_current()
        except MigrationOutOfDateError:
            if settings.migration_guard_fail_on_mismatch:
                raise
            logger.warning(
                "Continuing startup despite the schema mismatch above "
                "(migration_guard_fail_on_mismatch=False)."
            )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Enterprise Bid Decision Intelligence Platform",
    debug=settings.debug,
    lifespan=lifespan,
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

# Centralized service-exception -> HTTP mapping + logging (Phase 1.5
# findings #4 and #5) -- see app/core/exception_handlers.py. Routers no
# longer need their own try/except NotFoundError/ConflictError/... blocks.
register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["infrastructure"])
def health_check() -> dict:
    """
    Liveness only: is the process itself up and able to handle a request?
    Deliberately does nothing else -- no DB call, no AI call -- so Cloud
    Run's liveness probe (which restarts the container on repeated
    failures) never fires because of a transient database or LLM-provider
    issue that has nothing to do with the process itself being alive.
    """
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/db", tags=["infrastructure"])
def health_check_db() -> JSONResponse:
    """
    Readiness: can this instance actually reach the database? Deliberately
    separate from /health (Phase 3: GCP deployment) -- a Cloud Run
    readiness probe should stop routing traffic to an instance that can't
    reach Cloud SQL, but a liveness probe restarting the container
    wouldn't fix a database outage and would just thrash the process
    instead. One cheap `SELECT 1` against the existing connection pool --
    no AI calls, no document processing, nothing expensive.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database readiness check failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "unreachable"},
        )
    return JSONResponse(content={"status": "ok", "database": "reachable"})
