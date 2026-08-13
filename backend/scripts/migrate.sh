#!/usr/bin/env sh
# Deploy-time migration runner (Phase 3: GCP deployment).
#
# Deliberately NOT run automatically on every app container boot. Cloud
# Run can scale a service to multiple concurrent instances (including
# during a rolling deploy, where old and new revisions briefly run side
# by side); if every instance ran "alembic upgrade head" on startup, two
# instances starting at once could race to apply the same migration
# concurrently. Alembic has no built-in distributed lock for this.
#
# Instead this is meant to run exactly once, as its own Cloud Run Job
# (`gcloud run jobs execute bidops-migrate`), *before* deploying a new
# backend revision that depends on the schema it applies -- see
# docs/DEPLOYMENT.md for the exact command and full deploy order. Same
# Docker image as the app itself, just a different entrypoint -- this is
# still the one and only migration mechanism in the project (Alembic),
# never a second competing one; it only changes *when* it runs.
#
# The application's own migration_guard (app/core/migration_guard.py)
# still runs on every app instance's startup regardless -- it never
# trusts that this job was actually run, it re-checks the real schema
# state every time and refuses to serve traffic if it's still behind.

set -eu

echo "Running Alembic migrations against the configured DATABASE_URL..."
alembic upgrade head
echo "Migrations applied successfully."
