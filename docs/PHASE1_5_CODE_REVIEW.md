# Phase 1.5 Code Review — Non-AI-Cost Findings

Scope: everything `ENGINEERING_DIRECTIVE.md`'s "Post-Architecture Phase" and the founder's Phase 1.5 directive named — code quality, UX, accessibility, error handling, loading/empty states, performance, test coverage, documentation, deployment reliability, observability, security hardening, developer experience. No new AI features, no architecture changes proposed here — every item below is implementation-level, consistent with Principle 9 (`AI_ARCHITECTURE_PRINCIPLES.md`).

Read-only review — no code was changed to produce this document. Findings are ordered highest-impact / lowest-cost first within each area, then an overall priority call at the end.

---

## 1. Verify the OpenAI model configuration

**Problem:** `backend/app/core/config.py:76` defaults `openai_model` to `"gpt-5.6"`, and both `backend/.env` and `backend/.env.example` set it explicitly to the same value.
**Why it matters:** if this isn't a real, currently-available OpenAI model id, every real (non-mock) LLM call fails at the API boundary — the single most consequential possible finding in this review, since it would silently block tender processing the moment real API funding begins.
**Impact:** Critical if wrong, zero if right — this review can't tell which from the code alone; my training data predates whatever OpenAI has released most recently, so I can't independently confirm or deny it.
**Proposed solution:** A two-minute manual check against OpenAI's current model catalog before Phase 1.5 work begins in earnest, not a code change.
**Implementation complexity:** Trivial.
**Recommendation:** Do this first, before anything else in this document — it's a blocking check, not a nice-to-have.

---

## 2. `POST /missions/{id}/execute` has no rate limit

**Problem:** Every other cost-incurring endpoint carries `@limiter.limit(...)` (`evaluation.py:75`, `tenders.py:39/73/113`, `capabilities.py:69`), but `execute_mission` (`backend/app/api/v1/missions.py:92-109`) — which triggers the full Decision Engine LLM run — does not.
**Why it matters:** reopens the exact abuse vector RC-2 finding H-2 closed elsewhere; one unrated endpoint is enough to let a client hammer LLM spend even though every sibling endpoint is protected.
**Impact:** High (direct cost-control gap) for trivial effort.
**Proposed solution:** Add `@limiter.limit("10/minute")` matching `evaluation.py`'s existing rate.
**Implementation complexity:** Trivial.
**Recommendation:** Fix immediately.

---

## 3. No security response headers

**Problem:** CORS is well-configured (explicit allowlist, no wildcard — `backend/app/main.py:44-59`), but there's no `X-Content-Type-Options`, `X-Frame-Options`, or HSTS middleware anywhere.
**Why it matters:** cheap, standard hardening for a platform that will hold real procurement documents and company financial data; the absence is a gap an actual security review before a first customer would flag immediately.
**Impact:** Medium-high for small effort.
**Proposed solution:** A small Starlette middleware adding the standard headers, registered once in `main.py`.
**Implementation complexity:** Small.
**Recommendation:** Do this during Phase 1.5, before the first real customer.

---

## 4. Logging is thin and inconsistent outside the LLM path

**Problem:** Only 7 of ~20 backend modules call `logger.` at all; none of the 10 API routers log before translating a caught `NotFoundError`/`ConflictError` into an HTTP response (e.g. `backend/app/api/v1/missions.py:104-109`, `backend/app/api/v1/approval.py:52-59`). `document_service.upload_document`'s rollback path (`backend/app/services/document_service.py:41-46`) also logs nothing, unlike the equivalent pattern in `tender_service.py:119-121` and `capability_service.py:95-98`.
**Why it matters:** operators can currently only diagnose LLM-related failures from logs; the far more common 404/409/422 failures (auth, validation, conflicting state) leave no trace. This directly undercuts `logging_config.py`'s own stated bar ("an incident should be diagnosable").
**Impact:** Medium-high — this is an observability gap that will be felt the first time something goes wrong with a real customer, not before.
**Proposed solution:** One log line per except-block at minimum; better, a shared exception-to-HTTP mapper registered once via `app.add_exception_handler(...)` in `main.py` that logs and maps in one place instead of ~30 duplicated try/except blocks (see finding 5).
**Implementation complexity:** Medium.
**Recommendation:** High priority — pairs naturally with finding 5 below (same code you'd touch either way).

---

## 5. ~30 duplicated try/except blocks across routers

**Problem:** Every router repeats the identical `except NotFoundError → 404`, `except ConflictError → 409` pattern by hand (e.g. `missions.py:72-76,86-90,104-109`, `approval.py:51-59,71-79,88-93`).
**Why it matters:** it's consistent today, which is good, but it's copy-pasted rather than centralized — a change to the mapping (or adding the logging from finding 4) currently requires editing every router by hand, and nothing guarantees a future router won't forget one.
**Impact:** Medium — quality-of-life and consistency guarantee, not a bug today.
**Proposed solution:** A FastAPI exception handler registered once (`app.add_exception_handler(NotFoundError, ...)` etc.) removes ~40 lines of repetition and centralizes the logging fix from finding 4 at the same time.
**Implementation complexity:** Medium.
**Recommendation:** Do together with finding 4.

---

## 6. `approval_service.py` and `revalidation_service.py` have no dedicated tests

**Problem:** `tests/test_bid_decision.py`, `test_decision_engine_concurrency.py`, and `test_multi_tenancy.py` (680 lines combined) cover the decision/bid-decision flow and tenant isolation well. `approval_service.py` (162 lines — the actual bid/no-bid decision audit trail) and `revalidation_service.py` (264 lines — capability staleness cascade) have neither.
**Why it matters:** consistent with this project's own stated philosophy ("protect core guarantees, not chase coverage %" — see `test_multi_tenancy.py`'s docstring), these two are plausibly load-bearing enough to earn one focused test file each, not blanket coverage.
**Impact:** Medium — protects against regressions in exactly the two places a silent bug would be hardest to notice (an audit trail, and a cascading revalidation).
**Proposed solution:** One test file per service, following `test_multi_tenancy.py`'s existing template (real ORM objects, in-memory SQLite, one test per guarantee).
**Implementation complexity:** Medium.
**Recommendation:** Worth doing in Phase 1.5, no urgency.

---

## 7. Native `window.confirm()` used for every destructive action

**Problem:** `frontend/src/pages/Missions.tsx:169`, `Capabilities.tsx:119`, `Documents.tsx:83` all call `window.confirm(...)` for delete flows.
**Why it matters:** unstyled, blocks the JS thread, can't be branded or made keyboard-consistent, and is the only interaction in the entire app that isn't built from the shared `Card`/`Button`/`Toast` kit — a visible inconsistency the moment a real user hits delete.
**Impact:** Medium-high for the number of places it appears — one shared component fixes all three call sites.
**Proposed solution:** A `ConfirmDialog` kit component, built once and swapped in at all three sites.
**Implementation complexity:** Medium.
**Recommendation:** Good first Phase 1.5 UX fix — visible, cheap, and consistent with existing kit patterns.

---

## 8. "Active missions" filtering logic duplicated across three pages

**Problem:** `Missions.tsx:113-126`, `Dashboard.tsx:58-79`, and `Reports.tsx:45-62` each independently reimplement `status !== "archived"` and "reportable = has recommendation_id."
**Why it matters:** any future change to that rule (e.g. a new terminal `MissionStatus`) requires editing three files by hand and risks silent drift between them — exactly the kind of duplication this review was asked to find.
**Impact:** Medium — not a bug today, but a real maintainability liability.
**Proposed solution:** A shared `useActiveMissions()`/`useReportableMissions()` hook.
**Implementation complexity:** Medium.
**Recommendation:** Do alongside finding 7 — same general "extract shared logic" pass.

---

## 9. `Dropzone` is keyboard-inaccessible

**Problem:** `frontend/src/components/kit/Dropzone.tsx:73-88` is a plain `<div onClick=...>` with no `role="button"`, `tabIndex`, or key handling.
**Why it matters:** a keyboard-only user cannot reach or activate the upload target at all — a hard accessibility failure, not a nice-to-have, on the primary entry point of the product (tender/document upload).
**Impact:** High for the affected user population, trivial cost.
**Proposed solution:** Add `role="button" tabIndex={0}` plus Enter/Space key handling.
**Implementation complexity:** Trivial.
**Recommendation:** Fix immediately — this is the cheapest high-impact item in the entire review.

---

## 10. No ESLint/Prettier config, despite lint-disable comments already in the code

**Problem:** No `.eslintrc*`/`eslint.config.*` exists anywhere in `frontend/`, no `lint` script in `package.json`, and CI (`.github/workflows/ci.yml`) runs typecheck + build only — yet the codebase already scatters `// eslint-disable-next-line react-hooks/exhaustive-deps` comments (`TenderDetail.tsx:51`, `Missions.tsx:130`, `Dashboard.tsx:91`, `Capabilities.tsx:101`, `Evaluation.tsx:104`).
**Why it matters:** those disable comments are currently no-ops — nothing lints the project, so nothing is actually being suppressed, and nothing catches a real hook-rule violation before merge.
**Impact:** Medium — developer-experience and regression-prevention gap that compounds as more contributors touch the codebase.
**Proposed solution:** ESLint + `eslint-plugin-react-hooks` + Prettier, a `lint` script, and a CI step alongside the existing typecheck/build jobs.
**Implementation complexity:** Small-medium.
**Recommendation:** Do early in Phase 1.5 — cheap, and every day without it is another day of undetectable drift.

---

## 11. No frontend test tooling at all

**Problem:** No Vitest/Jest/RTL dependency, no `test` script — zero automated frontend regression coverage, including on non-trivial pure logic in `src/lib/complianceMerge.ts` and `src/lib/pdfReport.ts`.
**Why it matters:** the backend has a (deliberately narrow) test suite; the frontend has none, which is the more asymmetric gap given the frontend is ~4,100+ lines.
**Impact:** Medium — same "protect real guarantees, not blanket coverage" philosophy applies; start with the `lib/` helpers, which are pure functions and cheapest to test.
**Proposed solution:** Bootstrap Vitest + RTL, write a handful of smoke tests on `complianceMerge.ts` first (it's the one piece of logic two pages already depend on being correct).
**Implementation complexity:** Medium.
**Recommendation:** Start small — a handful of pure-function tests, not a full RTL page-test suite, matches this project's own stated testing philosophy.

---

## 12. `Evaluation.tsx` has grown to ~700 lines with four responsibilities in one file

**Problem:** the page component, `MatrixRow`, `BusinessDecisionPanel`, and `StatusStat` are all co-located in `frontend/src/pages/Evaluation.tsx` — the largest file in the app by a wide margin.
**Why it matters:** readability and testability — the two sub-components each carry their own local state now (verification form, decision form) and would benefit from being independently reachable/testable files.
**Impact:** Low-medium — purely a maintainability concern, not a bug.
**Proposed solution:** Split `MatrixRow` and `BusinessDecisionPanel` into their own files under `src/pages/evaluation/`.
**Implementation complexity:** Medium (mechanical, but touches the file most actively being worked on).
**Recommendation:** Defer until the next time this file needs a real change — don't refactor for its own sake mid-quiet-period.

---

## 13. Minor accessibility gaps: `SearchInput` clear button, `Menu` keyboard nav

**Problem:** `SearchInput.tsx:22-27`'s "×" clear button has no `aria-label`; `Menu.tsx` closes on outside-click but not `Escape`, and `MenuItem` has no arrow-key traversal.
**Why it matters:** both are used across every list page (Missions, Documents, Evaluation) — small individually, additive across the whole app for screen-reader and keyboard-only users.
**Impact:** Medium for the affected population, low engineering cost.
**Proposed solution:** `aria-label="Clear search"` (trivial); `Escape`-to-close + roving-tabindex on `Menu`/`MenuItem` (small).
**Implementation complexity:** Trivial + small.
**Recommendation:** Bundle with finding 9 as one "accessibility pass" batch.

---

## 14. `tsconfig.json` disables unused-code checks under an otherwise-strict config

**Problem:** `frontend/tsconfig.json:12-13` sets `noUnusedLocals: false, noUnusedParameters: false` while `strict: true` is on everywhere else.
**Why it matters:** inconsistent strictness posture — dead variables/imports can accumulate silently with nothing catching them at compile time.
**Impact:** Low-medium, compounding over time.
**Proposed solution:** Flip both to `true`; expect a small one-time cleanup of whatever's already accumulated.
**Implementation complexity:** Small.
**Recommendation:** Do alongside finding 10 (ESLint setup) — same "turn the strictness dial up" pass.

---

## 15. No deployment/containerization story documented anywhere

**Problem:** no `Dockerfile`/`docker-compose.yml` anywhere in the repo, and no deployment doc describing how `backend`/`frontend` actually get run in production. Relatedly, `rate_limit.py`'s in-memory (`slowapi`) limiter is honestly documented in its own module docstring as per-process/single-instance, but that constraint isn't surfaced anywhere a future deployer would see it before scaling horizontally.
**Why it matters:** "deployment reliability" was explicitly named in this review's scope; right now, reproducing this deployment (or scaling it) depends entirely on institutional memory rather than a written procedure.
**Impact:** Medium-high the first time someone other than the current maintainer needs to deploy or scale this.
**Proposed solution:** A minimal `docs/DEPLOYMENT.md` (even a paragraph: how it's run today, and "do not horizontally scale without swapping the rate limiter to a shared store first") is more valuable right now than a Dockerfile — write the doc before building infrastructure nobody's asked for yet (Technical Debt Policy, "Customer driven" category).
**Implementation complexity:** Trivial (doc) to medium (actual containerization, deferred).
**Recommendation:** Write the one-page doc now; defer Docker until an actual deployment target exists.

---

## 16. Documentation sprawl: 26 files in `docs/` with no index

**Problem:** `docs/` now holds 26 markdown files — the original numbered spec (`00_Project_Context.md` through `11_Risk_Assessment.md`), the frozen architecture docs, feature design docs, and audit reports — with no single index explaining which is authoritative for what, or which of the numbered `0X_*.md` docs are still current vs. superseded by `CORE_ARCHITECTURE.md`.
**Why it matters:** exactly the "documentation quality" dimension this review was asked to check — a new contributor (or a future Claude session without this conversation's context) has no fast way to know that `CORE_ARCHITECTURE.md`/`AI_ARCHITECTURE_PRINCIPLES.md`/`ENGINEERING_DIRECTIVE.md` are the frozen governing set and the numbered docs are historical.
**Impact:** Medium — a real onboarding-friction cost, not a functional bug.
**Proposed solution:** A short `docs/README.md` (or a table at the top of the root `README.md`) mapping each doc to its status: frozen/governing, historical/superseded, feature-specific, or audit-report.
**Implementation complexity:** Trivial.
**Recommendation:** Do this soon — it's the cheapest fix in this entire document relative to how much confusion it prevents.

---

## Overall Priority Call

Highest priority, do first (all trivial-to-small, several are pure risk-elimination):

1. Verify the OpenAI model string (#1) — blocking check, not a task.
2. Rate limit `execute_mission` (#2).
3. Fix `Dropzone` keyboard accessibility (#9).
4. Write the one-page deployment doc (#15).
5. Write the `docs/` index (#16).

Second wave (small-medium, real but not urgent):

6. Security response headers (#3).
7. Router logging + centralized exception handling (#4 + #5, same pass).
8. ESLint/Prettier + `noUnusedLocals` (#10 + #14, same pass).
9. Accessibility batch: `SearchInput`, `Menu` (#13).

Third wave (medium, worth doing but no urgency):

10. `ConfirmDialog` component (#7).
11. Shared active-missions hook (#8).
12. `approval_service`/`revalidation_service` tests (#6).
13. Frontend test tooling, starting with `lib/` (#11).

Deferred, revisit only if it becomes a real problem:

14. `Evaluation.tsx` split (#12) — wait for the next real change to that file.

No item in this document proposes a new AI feature, a new table, a new endpoint, or a change to `CORE_ARCHITECTURE.md`. Everything here is implementation-level, consistent with the Phase 1.5 directive.
