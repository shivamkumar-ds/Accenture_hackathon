# BidOps AI — backend production image (Phase 3: GCP deployment / Cloud Run).
#
# Single image, two uses:
#   - App:       CMD below (uvicorn), deployed as the Cloud Run *service*.
#   - Migration: `docker run ... /app/scripts/migrate.sh`, deployed as a
#     separate Cloud Run *Job*, run once before a new service revision
#     that needs the new schema. See scripts/migrate.sh and
#     docs/DEPLOYMENT.md for why this is a separate job, not part of the
#     app's own startup.
#
# Kept to one straightforward stage rather than a multi-stage build --
# this project has no compiled/native build step beyond psycopg2-binary
# (already a prebuilt wheel), so multi-stage would add complexity with no
# real image-size or build-time benefit here.

FROM python:3.12-slim

# Unbuffered stdout/stderr so log lines reach Cloud Logging as they're
# written, not batched and flushed late. bytecode compilation disabled --
# irrelevant for a container that starts once and runs, not worth the
# extra build time.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies installed before the rest of the source is copied in, so
# this layer is only rebuilt when requirements.txt actually changes --
# not on every source edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts/migrate.sh ./scripts/migrate.sh
RUN chmod +x ./scripts/migrate.sh

# Explicitly NOT copied into the image: .env / .env.example (config comes
# from Cloud Run environment variables and Secret Manager, never a
# bundled file -- see .dockerignore), tests/, venv/, storage/ (a fresh,
# empty directory only, and only relevant to the local-disk storage
# fallback -- see docs/DEPLOYMENT.md's File Storage section for why this
# does not survive Cloud Run's ephemeral filesystem as durable storage).

# Runs as a non-root user -- standard container hardening, no functional
# reason this process needs root.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Cloud Run injects PORT at runtime (defaults to 8080 if unset, matching
# Cloud Run's own default) and requires the container to actually bind to
# it -- $PORT must be resolved by a shell, so this uses the shell form of
# CMD rather than the exec-form JSON array.
ENV PORT=8080
EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
