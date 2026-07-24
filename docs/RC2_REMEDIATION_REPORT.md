# RC-2 Remediation — Implementation Report

Date: 2026-07-24
Scope: the five-item punch list agreed after the RC-2 audit, executed in order, no scope additions.

## 1. Secret-handling hardening — commit `cdb14f9`

Problem: the hand-off archive that produced the RC-2 audit contained a live Gemini API key, because it was zipped by hand rather than exported from git, and `.env` (gitignored) got swept in anyway.

Fix: added `scripts/safe_export.sh`, which runs `git archive --format=zip HEAD` — this can only ever contain committed, tracked files, so a gitignored `.env` structurally cannot end up in the output. The script also runs a post-export grep sanity check and refuses to leave a bad archive in place. Documented in `README.md` under "Handing off or exporting this repository," with the RC-2 finding cited as the reason it exists. No code path in the app itself changed — this was a tooling/process fix, not an application vulnerability.

Note: this does not rotate the already-leaked key — that's an action only you can take (revoke it at the provider console). The tooling prevents recurrence, it doesn't undo the original exposure.

## 2. Rate limiting — commit `b7c8a02`

Added `slowapi` (in-memory, IP-keyed limiter — no Redis, consistent with "keep it simple"). Limits applied to every endpoint named in the instructions:

- `POST /auth/register` — 5/hour
- `POST /auth/login` — 10/minute
- Document upload — 20/minute
- Tender upload — 20/minute
- Tender analysis run — 10/minute
- Capability build — 20/minute
- Evaluation run — 10/minute

Each limit was sized to the endpoint's actual cost: auth endpoints are cheap but abuse-prone (tight limits), LLM-backed endpoints are expensive per call (looser call-rate but still capped). `rate_limit_enabled` is a config flag (default on) so it can be disabled for local dev/testing without code changes. Verified with a manual TestClient run hitting `/auth/login` 12 times: requests 1–10 returned 401 (expected — wrong credentials), 11–12 returned 429.

## 3. Decision Engine bounded concurrency — commit `33be9cd`

`decision_service.run_evaluation()`'s per-requirement LLM matching loop was fully sequential. Replaced with `asyncio.Semaphore(settings.decision_engine_max_concurrency)` (default 5) + `asyncio.gather()`. `decision_engine.py` itself — the actual matching logic — was not touched.

All four things you required preserved, and each is covered by a dedicated test in `test_decision_engine_concurrency.py`:

- **Determinism / ordering** — `gather()` returns results in input order regardless of completion order; verified every `ComplianceMatrix` row still maps to its correct originating requirement.
- **Evidence mapping** — verified matched-entity/evidence data propagates identically to the old sequential path.
- **Error handling** — verified one failed match still fails the *whole* evaluation (same `ExtractionError`, nothing partially persisted) — not silently degraded to a partial success.
- **Bounded, not unlimited** — verified max concurrent in-flight calls never exceeds the configured limit, while still measurably faster than sequential.

## 4. Multi-tenancy regression tests — commit `520198f`

Added `test_multi_tenancy.py` — five tests, one per entity category you named: Documents, Missions, Tenders, Evaluations, Capability entities. Each test creates two companies, puts data under Company A, and asserts Company B gets `NotFoundError` (or `None` for capability entities — see below) when it tries to read it. Each test also confirms the positive path (Company A reading its own data) so a bug that denies *everyone* couldn't accidentally look like a pass.

One documented asymmetry: `capability_service.find_capability_by_id()` returns `None` for a cross-tenant lookup rather than raising `NotFoundError` like the other four services. Externally this still produces a 404 (the API layer maps `None` to 404), so behavior is consistent from the outside — the test file documents the internal difference rather than hiding it.

Sanity check before committing: I temporarily removed the `company_id` filter from `mission_service.get_mission()` and re-ran the suite — the mission and evaluation isolation tests correctly failed, confirming these tests actually catch a real regression rather than passing vacuously. Reverted before running anything further.

## 5. Minimal CI — commit `d102c7a`

`.github/workflows/ci.yml`, two independent jobs, nothing beyond what you asked for:

- **backend**: `pip install -r requirements.txt` → `pytest`
- **frontend**: `npm ci` → `tsc -b` → `vite build`

No database service container — the backend suite never touches real Postgres (every test builds its own in-memory SQLite DB). No deploy step, no Docker, no artifact publishing.

## Final verification sweep (run in the order you specified)

| Check | Result |
|---|---|
| 1. Full backend test suite | **55/55 passed** |
| 2. Evidence-trail verification script | **19/19 passed** |
| 3. Frontend type check (`tsc -b`) | **clean, 0 errors** |
| 4. Frontend production build (`vite build`) | **succeeded**, 1896 modules, no warnings beyond normal chunk-size notices |
| 5. Regressions | **none found** |

## What was deliberately not touched

Per your constraints, no schema changes, no UI changes, no prompt changes, no feature additions, no redesign of `decision_engine.py`. The rate limiter is in-memory (single-process) rather than Redis-backed — correct for current scale, and flagged in code comments as the first thing to revisit if you move to multiple backend workers. The already-leaked API key from the RC-2 finding still needs manual rotation at the provider console; that's outside what code changes can fix.

Engineering phase is frozen per your instruction. Ready to move to Swagger/API testing, frontend testing, real tender document testing, bug fixing, and deployment.
