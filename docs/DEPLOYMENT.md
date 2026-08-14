# Deployment

Phase 3 (GCP deployment) target architecture:

```
User
  |
  v
Frontend (Firebase Hosting -- static build)
  |
  v
Backend API on Cloud Run (Docker, this repo's backend/Dockerfile)
  |
  v
Cloud SQL for PostgreSQL
```

External services (Google OAuth, the configured LLM provider, and later
RevenueCat/billing and email) are reached directly by the backend using
environment variables and Secret Manager — nothing routes through a
separate service layer.

This document is the single source of truth for what's actually been
built for deployment vs. what still requires manual GCP setup. Nothing
below has been deployed yet — no GCP project ID or credentials were
provided when this was written. See "Verification status" at the bottom
for exactly what has and hasn't been checked.

## Why Firebase Hosting for the frontend

The frontend is a static Vite build (`dist/`) with no server-side
rendering — it doesn't need Cloud Run at all. Firebase Hosting is the
simplest GCP-native fit for "an early-stage SaaS, not overengineered":
free tier covers this project's traffic easily, HTTPS and a CDN are
automatic, custom domain support is built in, and there is no server to
patch or scale. The alternative (Cloud Storage bucket + Cloud Load
Balancer + managed SSL cert) is strictly more setup for the same result
and is not worth it at this stage. Revisit only if a real requirement
Firebase Hosting can't meet shows up later (it currently doesn't).

## The one constraint that governs everything else here

`backend/app/core/rate_limit.py` uses `slowapi`'s in-memory store —
correct for exactly one running backend process, silently wrong the
moment there's more than one (each instance keeps its own counter, so a
client could get up to N requests *per instance* instead of N total).
This was true before Cloud Run entered the picture and remains true now.

**For this deployment: set Cloud Run's max instances to 1**
(`--max-instances=1` at deploy time, see below). This keeps the existing
rate limiter correct with zero code changes, and is entirely adequate
for a hackathon demo / early customer's traffic. Moving the limiter to a
shared store (Redis, `slowapi`'s standard supported backend) is real
work that should happen deliberately, before intentionally scaling past
one instance — not implemented in this pass, since it isn't required to
ship the MVP target.

## Migration strategy: a separate Cloud Run Job, not auto-migrate-on-boot

The existing migration guard (`app/core/migration_guard.py`,
`docs/BUG_BUCKET.md` Bug #001) is unchanged and still runs on every app
instance's startup — it checks the database's real Alembic revision
against the code's migration head and refuses to serve traffic on a
mismatch, exactly as before. It does not, and still does not, run
migrations itself.

Migrations are applied via `backend/scripts/migrate.sh`, the same Docker
image, run once as its own **Cloud Run Job** — not automatically on every
app container boot. Reasoning: Cloud Run can run multiple concurrent
instances during a rolling deploy (old and new revisions briefly serving
traffic side by side); if every instance ran `alembic upgrade head` on
its own boot, two instances starting at once could race to apply the
same migration concurrently. Alembic has no built-in distributed lock
for that. A one-off Job, run to completion before the new service
revision is deployed, has no such race — it's a single execution, not one
per instance. This is still the one and only migration mechanism in the
project; only *when* it runs changed, not *what* runs it.

## Code completed this phase

- `backend/Dockerfile`, `backend/.dockerignore` — production image for
  Cloud Run. Non-root user, binds `$PORT`, unbuffered logs to
  stdout/stderr, no `.env`/tests/venv/local storage baked in.
- `backend/scripts/migrate.sh` — the Cloud Run Job entrypoint above.
- `backend/app/core/database.py`, `app/core/config.py` — explicit,
  conservative connection pool sizing (`DB_POOL_SIZE`,
  `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS`). `DATABASE_URL` was
  already fully environment-driven; no code change needed for Cloud SQL
  itself, just the Unix-socket connection string form documented in
  `.env.example`.
- `backend/app/main.py` — `GET /health/db` readiness check (cheap
  `SELECT 1`), distinct from the existing `GET /health` liveness check.
  Neither performs AI calls or document processing.
- `backend/app/core/storage.py` and its three call sites — `STORAGE_BACKEND`
  (`local`, unchanged default, or `gcs`). See "File storage" below.
- `backend/.env.example`, `frontend/.env.example` — every new variable
  documented; see "Environment variables" below for the full audit.
- `backend/requirements.txt` — added `google-cloud-storage` (only
  actually imported when `STORAGE_BACKEND=gcs`).

## File storage: local disk does not survive Cloud Run

Cloud Run's container filesystem is ephemeral and never shared across
instances — a file written by one request is not guaranteed to exist for
a later request, possibly on a different instance entirely, or after a
scale-to-zero and cold start. The existing local-disk implementation
(`storage/{company_id}/documents/{uuid}.ext`) is correct for local
development and would silently lose customer-uploaded tender/capability
documents in production.

**Minimum production-safe fix, already implemented:** `STORAGE_BACKEND=gcs`
routes every document read/write/delete through a Cloud Storage bucket
instead, using the exact same relative-path key layout — `Document.storage_path`
in the database never changes shape, so no data migration is needed for
the *metadata*. What manual action is required: create the bucket (see
"GCP resources required" below) and, if this deployment has pre-existing
locally-stored documents to carry over, copy them into the bucket at the
same relative paths (`gsutil -m cp -r storage/* gs://BUCKET/`) before
cutting over `STORAGE_BACKEND` to `gcs`. For a first deployment (the
Phase 3 target — no customers on it yet), there is nothing to copy.

## Environment variables

### Public frontend configuration (safe to embed in the built JS bundle)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend API origin, e.g. `https://bidops-api-xxxxx.run.app` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID — public by design, this is how Google's own Identity Services library is meant to be used |

### Backend configuration (not secret, but server-side)

| Variable | Purpose |
|---|---|
| `APP_NAME`, `APP_ENV`, `DEBUG` | `APP_ENV=production` for the real deployment — enables the `SECRET_KEY` fail-fast check and the HSTS header |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist — set to the real Firebase Hosting URL / custom domain, never `*` |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT config, non-secret |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS` | Connection pool sizing |
| `STORAGE_BACKEND`, `STORAGE_ROOT` | `gcs` for production |
| `LLM_PROVIDER`, `*_MODEL`, `*_TIMEOUT_SECONDS`, `*_MAX_RETRIES`, `*_RETRY_BACKOFF_SECONDS` | Provider selection and robustness tuning |
| `GEMINI_AUTH_MODE`, `GOOGLE_CLOUD_LOCATION` | Non-secret Gemini/Vertex config |
| `CAPABILITY_STALENESS_DAYS`, `TENDER_CHUNK_PAGE_SIZE`, `MAX_OPTIONAL_REVIEW_ITEMS`, `MAX_UPLOAD_SIZE_MB` | Business tuning, non-secret |
| `CONTACT_SENDER_EMAIL`, `CONTACT_NOTIFICATION_EMAIL` | Contact form email delivery (see secrets table below for `RESEND_API_KEY`) — `CONTACT_SENDER_EMAIL` must be an address/domain verified with Resend |

### Backend secrets — Secret Manager, never plain env vars in production

| Variable | Secret Manager secret name (suggested) | Notes |
|---|---|---|
| `DATABASE_URL` | `bidops-database-url` | Contains the DB password inline — treat the whole connection string as secret |
| `SECRET_KEY` | `bidops-jwt-secret` | JWT signing key — generate with `python -c "import secrets; print(secrets.token_hex(32))"`, never reuse the dev default |
| `GOOGLE_OAUTH_CLIENT_ID` | — (not secret, but still server config; can stay a plain env var) | Public identifier, listed here only because it pairs with the backend's ID-token verification |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `QWEN_API_KEY` | `bidops-openai-key` / `bidops-gemini-key` / `bidops-qwen-key` | Only the key(s) for `LLM_PROVIDER` actually in use are required |
| `GCS_BUCKET_NAME` | — (not secret) | Plain env var is fine |
| `RESEND_API_KEY` | `bidops-resend-key` | Contact form email delivery (see `app/core/email.py`) — if unset, the app still runs, and contact form submissions still persist; only the two notification/confirmation emails are honestly recorded as not-sent (`ContactSubmission.notification_status`/`confirmation_status`) |

Never expose any of the above through a `VITE_*` variable — that would
ship it into the public frontend bundle. Never commit real values;
`.env` is already gitignored on both sides, and `.env.example` files
contain no real credentials (verified via `git ls-files`).

## GCP resources required

- A GCP project (with billing enabled).
- Cloud SQL for PostgreSQL instance + database + user.
- Cloud Run service (backend) + Cloud Run Job (migrations — same image).
- Artifact Registry repository (to hold the built backend image).
- Secret Manager secrets (see table above).
- A Cloud Storage bucket (only if `STORAGE_BACKEND=gcs`, which is the
  recommended production setting).
- Firebase project + Hosting site (frontend) — can be the same GCP
  project via `firebase use --add`.
- An OAuth 2.0 Client ID in Google Cloud Console (APIs & Services →
  Credentials → OAuth client ID → Web application) for Google
  Authentication (Phase 2).

## Manual steps (exact commands, fill in your own PROJECT_ID/REGION/etc.)

These are illustrative `gcloud`/`firebase` commands — review each before
running; none of this has been executed against a real project.

```bash
# 1. GCP prerequisites
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com \
  storage.googleapis.com

gcloud artifacts repositories create bidops --repository-format=docker \
  --location=REGION

# 2. Cloud SQL
gcloud sql instances create bidops-db --database-version=POSTGRES_15 \
  --tier=db-g1-small --region=REGION
gcloud sql databases create bidops --instance=bidops-db
gcloud sql users create bidops --instance=bidops-db --password='REAL_PASSWORD'

# Secrets
printf 'postgresql+psycopg2://bidops:REAL_PASSWORD@/bidops?host=/cloudsql/PROJECT_ID:REGION:bidops-db' \
  | gcloud secrets create bidops-database-url --data-file=-
python -c "import secrets; print(secrets.token_hex(32))" \
  | gcloud secrets create bidops-jwt-secret --data-file=-
printf 'YOUR_OPENAI_KEY' | gcloud secrets create bidops-openai-key --data-file=-

# GCS bucket (if STORAGE_BACKEND=gcs)
gcloud storage buckets create gs://bidops-documents-PROJECT_ID --location=REGION

# 3. Build + push the backend image
cd backend
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/bidops/backend:latest

# 4. Run migrations (Cloud Run Job) -- BEFORE deploying the service
gcloud run jobs create bidops-migrate \
  --image=REGION-docker.pkg.dev/PROJECT_ID/bidops/backend:latest \
  --region=REGION \
  --set-secrets=DATABASE_URL=bidops-database-url:latest \
  --set-cloudsql-instances=PROJECT_ID:REGION:bidops-db \
  --command=/app/scripts/migrate.sh
gcloud run jobs execute bidops-migrate --region=REGION --wait

# 5. Deploy the backend service
gcloud run deploy bidops-api \
  --image=REGION-docker.pkg.dev/PROJECT_ID/bidops/backend:latest \
  --region=REGION \
  --allow-unauthenticated \
  --max-instances=1 \
  --add-cloudsql-instances=PROJECT_ID:REGION:bidops-db \
  --set-secrets=DATABASE_URL=bidops-database-url:latest,SECRET_KEY=bidops-jwt-secret:latest,OPENAI_API_KEY=bidops-openai-key:latest,RESEND_API_KEY=bidops-resend-key:latest \
  --set-env-vars=APP_ENV=production,LLM_PROVIDER=openai,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=bidops-documents-PROJECT_ID,ALLOWED_ORIGINS=https://YOUR-FIREBASE-SITE.web.app,GOOGLE_OAUTH_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com,CONTACT_SENDER_EMAIL=YOUR_VERIFIED_SENDER@yourdomain.com,CONTACT_NOTIFICATION_EMAIL=bidops.ai@gmail.com

# 6. Frontend
cd ../frontend
echo "VITE_API_BASE_URL=https://YOUR-CLOUD-RUN-URL" > .env.production
echo "VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com" >> .env.production
npm run build
firebase init hosting   # once, if not already set up; public dir = dist
firebase deploy --only hosting

# 7. Google OAuth production configuration (Google Cloud Console, manual —
#    no CLI equivalent):
#    APIs & Services -> Credentials -> your OAuth Client ID -> edit:
#      Authorized JavaScript origins: https://YOUR-FIREBASE-SITE.web.app
#      (add your custom domain too, once you have one)
#    No redirect URI needed -- Google Identity Services' ID-token flow
#    used here doesn't redirect through Google's servers.
```

## Deployment order

1. GCP prerequisites (enable APIs, create Artifact Registry repo).
2. Cloud SQL instance + database + user + secrets.
3. Build the backend image, run the migration Job — database must be at
   the code's migration head *before* step 4.
4. Deploy the backend Cloud Run service (`--max-instances=1`, see the
   rate-limiter constraint above).
5. Deploy the frontend to Firebase Hosting, pointed at the real backend URL.
6. Configure the OAuth Client ID's Authorized JavaScript origins to the
   real frontend URL.
7. Final verification — smoke test below, using the real production URLs.

## Production smoke test

Run through this against the real deployed URLs, not localhost:

- [ ] Register a new company + administrator (`/auth/register`)
- [ ] Log out, log back in with that password (`/auth/login`)
- [ ] Sign in with Google, for an account that was added via `POST /users`
      or is the registering admin's own email (confirms the login/link
      flow — see `docs/BUG_BUCKET.md`'s Phase 2 commits for why it never
      creates a company on its own)
- [ ] Register a *second* company, confirm it cannot see the first
      company's data anywhere in the UI (company isolation)
- [ ] Upload a company document (certification/CV/project cert)
- [ ] Build a capability from that document
- [ ] Upload a tender PDF
- [ ] Run tender analysis (requirement extraction)
- [ ] Run evaluation (Decision Engine) and confirm a Recommendation appears
- [ ] Review the gap analysis / compliance matrix
- [ ] Record a Business Decision (approve/reject) on the Decision screen
- [ ] Confirm the audit/decision history reflects it
- [ ] Log out, confirm the app correctly requires login again

## Verification status

**Verified locally:** full backend test suite (39/39, excluding one
pre-existing sandbox-only `test_llm_client.py` failure unrelated to this
work), `tsc --noEmit` + `vite build` clean, app imports cleanly with the
new config, both `/health` routes registered, single Alembic migration
head confirmed, `.env.example` files contain no real credentials
(`git ls-files` audit).

**Prepared but requires GCP to verify:** the Dockerfile itself was not
built (no Docker available in this environment) — reviewed manually
against the actual repo file layout, all `COPY` sources confirmed
present. Cloud SQL connectivity, the migration Job, GCS upload/download
against a real bucket, Google OAuth against a real Client ID, Firebase
Hosting deploy, and the full smoke test above are all unverified until
actually run against a real GCP project.

**Actually verified in GCP:** nothing yet — no project ID or credentials
were provided for this phase.
