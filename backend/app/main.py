"""
BidOps AI — Application entrypoint.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging

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

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["infrastructure"])
def health_check() -> dict:
    """Unversioned infrastructure health check — not part of the business API."""
    return {"status": "ok", "environment": settings.app_env}
