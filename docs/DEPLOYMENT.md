# Deployment

Phase 1.5 finding #15. There is no production deployment yet — this
documents how BidOps runs today and the one operational constraint that
matters before that changes. Not a deployment guide for a target that
doesn't exist yet.

## How it runs today

Local processes only: backend (`uvicorn app.main:app --reload`, see
`backend/README.md`) and frontend (`npm run dev`, see
`frontend/README.md`), both against a local PostgreSQL instance. No
containerization, no orchestration, no CI/CD deploy step. Setup for
either side is already fully documented in their respective READMEs —
this doc doesn't repeat those steps, only what's missing from them.

Health check: `GET /health` (`backend/app/main.py`), unauthenticated,
for basic liveness checks once something is actually polling it.

## The one constraint to know before deploying

`backend/app/core/rate_limit.py` uses `slowapi`'s default in-memory
store — counters live in a single process's memory, keyed by client IP.
This is correct for one backend instance. It silently stops being
correct the moment there's more than one: each instance would keep its
own counter, so a client could get up to N requests per instance instead
of N total, and the limit would no longer mean what it says.

**Do not run multiple backend instances (horizontal scaling, multiple
Uvicorn/Gunicorn workers, multi-pod deployment) without first moving the
limiter to a shared store** (Redis is `slowapi`'s standard supported
backend). Single-instance deployment — one process, scaled vertically if
needed — is safe as-is.

## What's deliberately not here

No Dockerfile, no deployment target, no infra-as-code. Per the
project's Technical Debt Policy ("Customer driven" — `ENGINEERING_DIRECTIVE.md`),
building container/deploy infrastructure now would be speculative: there's
no deployment target yet to build it against. That work is scoped for
the upcoming GCP deployment phase, once it starts.
