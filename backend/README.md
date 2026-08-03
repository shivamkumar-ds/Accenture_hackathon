# BidOps AI — Backend

Enterprise Bid Decision Intelligence Platform — v1.0.

Continuously understands company capability, evaluates tender requirements against it,
and produces evidence-backed, explainable recommendations — with humans holding final
authority over every consequential decision, and the platform staying trustworthy as
company capability changes over time.

## Structure

- `app/api/` — API layer (routers, request/response handling)
- `app/core/` — configuration, database connection, security
- `app/agents/` — AI agents and their prompts (Capability Builder, Tender Analysis, Decision Intelligence)
- `app/services/` — business logic and persistence, including the Mission Orchestrator (`mission_service.py`)
- `app/models/` — SQLAlchemy models (data layer)
- `app/schemas/` — Pydantic request/response schemas
- `alembic/` — database migrations
- `99_DECISIONS_LOG.md` — every engineering decision made, in order, with reasoning

## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values — see Configuration below
alembic upgrade head
uvicorn app.main:app --reload
```

Requires a running PostgreSQL instance matching `DATABASE_URL` in `.env`.

## Database Migrations

Whenever you pull backend code that includes a new migration (anything new under
`alembic/versions/`), run this **before** starting the server:

```
cd backend
source venv/bin/activate
alembic upgrade head
```

This is not optional housekeeping. If the database schema falls behind the code — a
migration exists but hasn't been applied — every query touching the changed table fails
with a raw `UndefinedColumn` error, and it looks like a random runtime bug rather than what
it actually is. See `docs/BUG_BUCKET.md` Bug #001 for exactly this happening.

To make this impossible to miss, the app checks its own schema at every startup
(`app/core/migration_guard.py`): it compares the database's current Alembic revision
against the code's migration head and, on a mismatch, aborts startup with a clear message
instead of letting the process boot and fail later on the first request that touches the
changed table. This is generic — it reads both revisions through Alembic's own APIs, so it
requires no maintenance as new migrations are added. Controlled by two settings
(`MIGRATION_GUARD_ENABLED`, `MIGRATION_GUARD_FAIL_ON_MISMATCH`, both default `true`) — see
`app/core/config.py` for what each one does.

## Configuration

All configuration lives in `app/core/config.py` (`Settings`) — nothing reads environment
variables directly anywhere else in the codebase. See `.env.example` for every variable,
with the reasoning for each default in `99_DECISIONS_LOG.md`. Notable ones:

- `LLM_PROVIDER` — `openai` (operational reference implementation — the only provider with
  a verified end-to-end Decision Engine run), `gemini` (Vertex AI mode via `GEMINI_AUTH_MODE
  =vertex` is the strategic long-term provider, pending equivalent real production
  verification), `qwen` (frozen — Alibaba Cloud/DashScope is unreachable for new accounts
  from this deployment's region), or `mock` (local testing without credentials).
  **Defaults to `mock` in code, intentionally** — every real provider is opt-in via
  explicit configuration, never a silent default (ADR-001). The recommended value for a
  real running instance is `openai`; see D-143 in the decision log for the full
  provider-strategy reasoning.
- `OPENAI_TIMEOUT_SECONDS` / `_MAX_RETRIES` / `_RETRY_BACKOFF_SECONDS`, `QWEN_*`,
  `GEMINI_*` — each provider's robustness settings, all bounded exponential-backoff on
  transient/network failures only; authentication failures are never retried, and
  malformed LLM *response content* (as opposed to a failed request) is explicitly out of
  scope here — see `app/agents/llm_exceptions.py`.
- `ALLOWED_ORIGINS` — comma-separated list of frontend origins CORS will accept. Defaults
  to the local Vite dev server; a real deployment must set this explicitly. Never a
  wildcard.
- `SECRET_KEY` — the shipped default is refused at startup outside `APP_ENV=development`
  (fails fast, does not silently boot insecurely — see D-143).
- `CAPABILITY_STALENESS_DAYS` (default 180), `TENDER_CHUNK_PAGE_SIZE` (default 5),
  `MAX_OPTIONAL_REVIEW_ITEMS` (default 2), `MAX_UPLOAD_SIZE_MB` (default 50) — none of
  these numbers are specified anywhere in the frozen architecture; each is a deliberate,
  documented default, configurable rather than hardcoded.

## The Platform, End to End

A single continuous workflow, in the order a real user would move through it:

1. **Auth & Company** (`/auth`, `/users`, `/company`) — `POST /auth/register` creates a
   Company and its first Administrator atomically; `POST /auth/login` and
   `GET /auth/profile` handle ongoing sessions. `POST /users` (Administrator-only) adds
   further users to an existing company.
2. **Document Upload** (`/documents`) — company-scoped local storage
   (`storage/{company_id}/documents/{uuid}.{ext}`), with file type/size validation and
   server-generated filenames (never client-derived).
3. **Capability Builder** (`/capabilities/build`) — extracts structured Certifications,
   Employee CVs, and Project Completion Certificates from uploaded documents, with full
   provenance, confidence scoring from measurable signals (never an LLM self-report), and
   OCR fallback for scanned PDFs.
4. **Capability Graph** (`GET /capabilities`, `GET /capabilities/{id}`) — the full company
   capability graph grouped by domain, with freshness (`is_expired`, `is_stale`,
   `freshness_status`) computed fresh on every request and never persisted.
5. **Tender Analysis** (`/tenders`, `/analysis/run`) — uploading a tender creates an inert
   Mission alongside it; analysis runs a chunk-and-merge pipeline over the full document
   (tested against real 15+ page tenders), with page-level provenance and deterministic
   duplicate removal.
6. **Decision Intelligence** (`/evaluation`, `/recommendations`) — matches every
   requirement against the capability graph, applies a deterministic freshness override
   (expired evidence forces `NOT_MET`; stale evidence only ever downgrades `MET` to
   `REVIEW_REQUIRED`, never rejects), and produces a Recommendation with weighted, capped
   confidence propagation and a fully deterministic executive summary — the only LLM call
   anywhere in this stage is the per-requirement match itself.
7. **Mission Orchestrator** (`/missions/{id}/execute`) — coordinates Tender Analysis and
   Decision Intelligence by calling their existing functions directly. Whether a stage
   needs to (re)run is decided by authoritative status (`Tender.processing_status`,
   `Mission.status`), never by checking whether output rows exist.
8. **Human Approval** (`/compliance/{id}/verify`, `/approval`) — governs the lifecycle of
   an already-generated recommendation; never regenerates anything. Only compliance rows
   that are both flagged and `HIGH`/`CRITICAL` risk block a decision; the human's actual
   decision lives only in `AuditLog`, and the AI's original Recommendation is never
   modified, even when a human's final call overrides it.
9. **Event-Driven Revalidation** (`PATCH`/`DELETE /capabilities/{id}`,
   `POST /capabilities/check-freshness`) — dependency-driven (traverses
   `CapabilityMapping → ComplianceMatrix → Recommendation → Mission`, never scans every
   Recommendation), coalesces to at most one new Recommendation per affected mission, and
   never touches history: a mission already `COMPLETED` gets a new Recommendation for
   current operational awareness while its original decision stays completely untouched.
   Use `GET /missions/{id}/recommendations` to see the full history — `Mission.recommendation_id`
   deliberately stops being "the latest" once a completed mission has been revalidated.

Every stage above enforces company isolation and authentication; mutating actions that
touch core company data (`/users`, capability `PATCH`/`DELETE`, `check-freshness`)
require the Administrator role, and mission approval accepts Executive or Administrator.

## Status

All ten Phase 1 milestones (M0–M10) are complete. This is **BidOps_Final**, the single
canonical codebase as of the consolidation recorded in D-143 — the prior separate Vertex AI
and OpenAI Build Week repositories are now permanent, read-only historical references; all
future development happens here.

**Real, verified, and operational today:** OpenAI (`OpenAIClient`) — end-to-end, including
the Decision Engine, verified during OpenAI Build Week. This is the operational reference
implementation.

**Real, implemented, offline-verified, pending real production execution:** Gemini via
Vertex AI (`GeminiClient`, `GEMINI_AUTH_MODE=vertex`) — the strategic long-term provider
(see D-142 for why). Two of three pipelines have real Gemini Developer API verification;
the Decision Engine specifically has never completed a real Vertex AI call. This is
deployment-gated — it requires `gcloud`/ADC and real network access to Google's endpoints
that no development sandbox in this project's history has had. Owner: whoever next deploys
this to a real GCP-reachable environment. See D-142's outstanding items.

**Frozen, not deleted:** Qwen (`QwenClient`) — DashScope is unreachable for new accounts
from every deployment region tried so far. Kept working and tested; revisit only if that
platform restriction changes.

See `99_DECISIONS_LOG.md` for the complete, chronological record of every engineering
decision, bug found and fixed, and the reasoning behind each — this is the single source
of truth for *why* the system is built the way it is, not just what it does.
