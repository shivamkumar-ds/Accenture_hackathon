# Bug Bucket

A permanent, running log of every production-affecting or development-blocking bug found
in BidOps, in order — what happened, why, how it was fixed, and what now prevents the same
class of bug from recurring. This is not a task tracker; entries are never deleted, only
appended.

## Bug Lifecycle

Every bug logged here follows the same seven steps, without exception (see
`docs/ENGINEERING_DIRECTIVE.md`'s "Bug handling policy" — this is a project-wide
engineering rule, not just a documentation convention):

```
1. Bug discovered
2. Root cause identified
3. Permanent fix implemented
4. Regression prevention mechanism added
5. BUG_BUCKET.md updated
6. Documentation updated (if applicable)
7. Regression tested
```

**Engineering Principle:** Never fix only the symptom. Whenever practical, every bug should
leave the codebase stronger than before by preventing the same class of issue from
happening again.

An entry below is not "done" until steps 4 and 7 are visible in it — a prevention mechanism
that exists in the codebase, and a test (or equivalent verification) that proves it actually
catches the bug's own failure mode, not just that the immediate symptom went away.

---

## Bug #001

**Title:** Database schema out of sync after Alembic migration

**Status:** Closed — 4 August 2026

**Date:** 4 August 2026

**Severity:** High

**Category:** Backend / Database

### Symptoms

- Tender Workspace failed to load.
- Tender listing (`GET /api/v1/missions`) failed.
- Upload Tender related queries failed.
- Every affected request returned `sqlalchemy.exc.ProgrammingError` wrapping
  `psycopg2.errors.UndefinedColumn: column tenders.category does not exist`.

### Root Cause

A new migration (`f4a7c2e1b9d3_add_category_to_tenders.py`) added a `category` column to
the `tenders` table, and the application code (model, schema, queries) was updated to
reference it. The backend server was started against a local PostgreSQL database that had
not had this migration applied — `alembic upgrade head` was never run before the server
was restarted. The code and the database schema silently drifted out of sync: the ORM
issued queries selecting `tenders.category`, a column that did not exist yet on disk.

This surfaced as a runtime 500 error deep inside a SQLAlchemy stack trace, discovered only
by using the app (opening Tender Workspace), rather than as an immediate, obvious signal at
the moment the mismatch was introduced.

### Fix

Immediate:

```
cd backend
alembic upgrade head
```

Permanent (see Prevention below):

- Implemented automatic migration revision verification at FastAPI startup
  (`app/core/migration_guard.py`), reusing the application's single shared database engine
  (`app/core/database.py`) rather than opening a second connection pool just for this check.
- Clear, large, developer-facing error message showing both revisions and the exact fix
  command; a diverged/multi-head migration history is also caught and surfaced with the
  same clear message type, instead of a bare Alembic error.
- Startup blocked (fatal `MigrationOutOfDateError`) when the schema is outdated, by default
  in every environment.
- `backend/README.md` updated with a "Database Migrations" section documenting the
  requirement and the guard.
- `backend/tests/test_migration_guard.py` — automated regression suite (step 7 of the Bug
  Lifecycle above): a stale database, an unmigrated database, and a diverged migration
  history must all raise; a matching database must not.

### Prevention

The backend now validates database schema compatibility before serving a single request.
On startup, `check_migrations_current()` compares the database's current Alembic revision
(read via `alembic.runtime.migration.MigrationContext`) against the code's migration head
(read via `alembic.script.ScriptDirectory`) — both through Alembic's own APIs, with no
revision ID ever hardcoded, so this works unmodified for every future migration with zero
manual maintenance.

On a mismatch, the app logs a large, unambiguous message (current revision, latest
revision, and the exact `alembic upgrade head` command) and aborts startup by raising
`MigrationOutOfDateError`, by default in every environment including production
(`Settings.migration_guard_fail_on_mismatch`, default `true`). An operator can opt a
production deployment into "log and continue" instead via that same setting if they've
deliberately decided a warning is preferable to startup downtime for their process — the
check still runs and still logs loudly either way.

### Engineering Rule

**Treat migration mismatches as fatal startup errors, never runtime errors.** A developer
should discover the problem the instant they start the server — not after navigating
through the application into the one screen whose query happens to touch the changed
table. This is now a permanent, generic safety system, not a one-off fix for the `category`
column specifically.

### Investigation Addendum: "Failed Tender Delete" (ruled out as a second bug)

**Original user observation.** While diagnosing what turned out to be this bug, the founder
separately reported: uploaded a tender PDF; extraction did not complete successfully and the
tender showed a Failed-type status instead of Success/Completed; clicked Delete on that
tender; immediately afterward, Tender Workspace stopped displaying tenders — for other
accounts too, not just the one that triggered it. This was flagged as a possible second,
distinct bug and explicitly re-opened for investigation rather than being assumed away.

**Why "delete a failed tender" was initially suspected.** The reported sequence — upload,
failure, delete, then breakage — plausibly pointed at the delete path mishandling a tender
whose upload/analysis never reached a clean terminal state (e.g. a null/dangling document
reference, an unhandled exception in the delete or subsequent list query). That's a
reasonable, distinct failure mode from a migration mismatch, so it was treated as an open
question rather than folded into Bug #001 by assumption.

**Exact reproduction scenario.** Built with real service-layer code (`mission_service`)
against an in-memory SQLite database, no assumptions substituted for execution:
1. Create a Company, User, Document, Mission, and Tender exactly as `tender_service.upload_tender()`
   would leave them (`Tender.processing_status = "pending"`, a real, already-persisted
   Document row — a Tender is never created without one, by construction).
2. Force `tender_analyzer.analyze_tender()` to raise, simulating a genuinely unparseable PDF,
   and drive it through `mission_service.execute_mission()` exactly as the app does.
3. Delete (archive) the resulting mission via `mission_service.archive_mission()`.
4. List missions again via `mission_service.list_missions()` plus the same
   tender/document-attachment logic `GET /api/v1/missions` uses.
5. Repeat steps 1–4 for a second, unrelated company with a healthy tender present in the same
   database at the same time, to directly test the "other accounts too" part of the report.

**What was actually verified, not assumed.**
- The failure is already handled correctly: `ExtractionError` propagates cleanly (no bare/
  unhandled exception), `Tender.processing_status` becomes `"failed"`, `Mission.status`
  reverts to `"created"` (there is no `FAILED` value in the frozen `MissionStatus` enum, by
  design — reverting keeps the mission retryable), and zero `Requirement` rows are created
  (no orphaned data from the partial run).
- Deleting (archiving) that mission raises no exception and leaves the Document row
  completely untouched — archiving a Mission never touches Document rows at all.
- Listing missions immediately afterward raises no exception and returns the correct,
  now-archived row with the right tender name resolved.
- Running the same sequence for Company A while Company B has an untouched, healthy tender
  in the same database: Company B's list is completely unaffected — same row count, same
  status, same tender.

**Why cross-company isolation rules out a failed-tender corruption bug.** The reported
symptom was every account losing Tender Workspace simultaneously, not just the account that
owned the failed tender. `mission_service.archive_mission()` and `mission_service.list_missions()`
are both filtered by `company_id` at the query level — there is no code path in this workflow
by which one company's tender, in any state, can affect a query scoped to a different
`company_id`. If corrupted delete handling for one failed tender were the cause, only that
one company's Tender Workspace would have broken; the "other accounts too" detail is
therefore evidence *against* this being the cause, not evidence for it.

**Why the global schema mismatch fully explains the observed behavior.** A missing database
column, by contrast, breaks every query against that table for every row, regardless of
which company owns it — because the query never gets far enough to filter by `company_id` at
all; it fails at the SQL level first. That is the only failure mode in this codebase capable
of taking down Tender Workspace for every account at once, and it is exactly what
`UndefinedColumn: tenders.category` was already proven to do (see Symptoms/Root Cause
above). The timing the founder described ("at roughly the same time there was also a
database migration issue") and the specific "affects everyone" signature both match Bug
#001 precisely, and neither matches a single-tender delete bug.

**Conclusion: no second bug found.** Bug #001 alone fully explains the reported behavior.
This was demonstrated by reproduction, not assumed — see the four passing tests below.

**Regression tests.** `backend/tests/test_failed_tender_delete.py` (4 tests) now permanently
covers this exact workflow: `test_failed_analysis_sets_expected_status_with_no_orphans`,
`test_deleting_a_failed_tender_does_not_raise`,
`test_listing_missions_after_deleting_a_failed_tender_does_not_raise`, and
`test_deleting_a_failed_tender_never_affects_another_company` (the direct test of the
cross-company claim above). If a future change ever does make this path unsafe, these tests
fail immediately instead of the conclusion silently going stale.

### Closure

Closed 4 August 2026 after a founder final review confirmed the subsystem covers: stale
schemas, unmigrated databases, diverged migration histories, and a codebase with zero
migration files — each with a clear, developer-facing message and a passing regression
test (`backend/tests/test_migration_guard.py`, 5 tests). No revision ID is hardcoded
anywhere in the implementation. This subsystem is now considered permanent infrastructure;
per the Bug Lifecycle above, it does not require further architectural work unless a real
production issue is found.

---

## Bug #002

**Title:** `run_analysis()` could crash uncleanly and strand a Tender in PROCESSING if its
Document lookup ever failed

**Status:** Closed — 4 August 2026

**Date:** 4 August 2026

**Severity:** Low (defensive hardening — not observed in production; found during the
Phase 1 Backend Stabilization Audit, not reported by a user)

**Category:** Backend / Error handling

### Symptoms (would-be, if triggered)

None observed in practice. Found by code review during the stabilization audit: in
`tender_service.run_analysis()`, the lookup of the Tender's linked `Document` row and the
resolution of its storage path happened *outside* the `try/except` that handles analysis
failures. `Tender.processing_status` was already committed to `PROCESSING` immediately
before this block.

### Root Cause

`document = db.get(Document, tender.uploaded_document)` followed directly by
`document.storage_path` — if `db.get()` ever returned `None`, the very next line raised a
bare `AttributeError`. That exception was not caught anywhere on this path, so it would
have surfaced as an unclean 500 to the caller, and — because it occurred after
`processing_status` was already set to `PROCESSING` and committed, but before anything ever
sets it to `FAILED` — the Tender would be left stuck in `PROCESSING` permanently, with no
retry path available through the UI.

Not reachable through the normal upload flow today: `upload_tender()` always creates the
Document before the Tender, and `Document` rows are soft-deleted only, with
`document_service.delete_document()` explicitly blocked (`ConflictError`) while any active
Tender still references it. So this specific `None` cannot currently occur. It was flagged
anyway because the stabilization audit's explicit goal is "every endpoint either succeeds
or fails with a clean business error," and a bare `AttributeError` plus a permanently stuck
status violates that even for an invariant that's expected to hold today.

### Fix

`backend/app/services/tender_service.py::run_analysis()` — the Document lookup, `None`
check, and storage path resolution now live inside the same `try/except` block as the
analyzer call. A missing Document now raises `ExtractionError` (caught, re-raised as-is —
not double-wrapped) and `Tender.processing_status` is set to `FAILED`, exactly like any
other analysis failure, instead of crashing uncaught and leaving the row stuck.

### Prevention

The fix is structural, not a special-cased `None` check bolted on separately: any future
failure introduced anywhere in this block (a new lookup, a new resolution step) is now
automatically covered by the same failure handling, because it's inside the `try`, not
because someone remembered to add a check for it.

### Engineering Rule

**A `Tender`/`Mission`/`Document`'s "in progress" status must never be set without a
guaranteed corresponding path back out of it.** Any code that transitions a row into an
in-progress state must have every subsequent statement, up to and including the final
terminal-state write, inside the same error handling — not just the one call that's
*expected* to fail.

### Regression tests

`backend/tests/test_tender_analysis_failure_modes.py` —
`test_run_analysis_with_missing_document_fails_cleanly_not_stuck`: forces exactly this
condition (a Tender referencing a nonexistent Document) and asserts `ExtractionError` is
raised and `processing_status` ends at `FAILED`, not stuck at `PROCESSING`.

---

## Bug #003

**Title:** `execute_mission()` guarded against double-execution with a non-atomic
check-then-write, leaving a race window

**Status:** Closed — 4 August 2026

**Date:** 4 August 2026

**Severity:** Medium (real concurrency bug, plausible in production — a double-click on
"Run Analysis," two open tabs, or a client-side retry after a slow response; found during
the Phase 1 Backend Stabilization Audit's race-condition review, not reported by a user)

**Category:** Backend / Concurrency

### Symptoms (would-be, if triggered)

None observed in production. Found by review: `mission_service.execute_mission()` read
`mission.status`, raised `ConflictError` if it was already `RUNNING`, and then — as a
*separate* statement — set `mission.status = RUNNING` and committed. Between the read and
that write, nothing prevented a second, concurrent call for the same mission from also
reading the pre-`RUNNING` status and also passing the guard. Both requests would then
proceed to run tender analysis and/or evaluation concurrently against the same mission:
duplicate LLM calls (real cost), duplicate `Requirement`/`Recommendation` rows, and
whichever commit landed last silently overwriting the other's state.

### Root Cause

A classic check-then-act race: the guard and the mutation were not atomic with respect to
the database. SQLAlchemy's ORM-level read (`get_mission()`) does not take any row lock, so
two concurrent transactions in Postgres's default `READ COMMITTED` isolation can both read
the same pre-transition status before either commits.

### Fix

`backend/app/services/mission_service.py` — added `_try_transition_to_running()`, which
replaces the read-then-write with a single atomic
`UPDATE missions SET status = 'running' WHERE id = :id AND status = :expected_status`. Only
one concurrent transaction's `WHERE` clause can still match by the time its `UPDATE`
executes; the database itself is the compare-and-swap. `execute_mission()` now checks the
returned row count: `1` means this call won the transition and proceeds; `0` means another
request already changed the mission's status, and it raises `ConflictError` (same
externally-visible contract as before) instead of silently proceeding.

### Prevention

The guard is now enforced by the database's own atomicity guarantee for a single
`UPDATE` statement, not by application-level timing — there is no window between "check"
and "act" left for a second concurrent request to slip through, no matter how the two
requests happen to interleave.

### Engineering Rule

**Any state transition used as a concurrency guard (a "claim this row" operation) must be
a single atomic statement, never a separate read followed by a separate write.** A
`SELECT` followed by an `if`/`UPDATE` is never a safe way to prevent two concurrent callers
from both proceeding, regardless of how unlikely the interleaving looks in normal use.

### Regression tests

`backend/tests/test_mission_execute_race.py` —
`test_concurrent_transition_to_running_only_succeeds_once`: opens two independent database
sessions against the same mission (simulating two concurrent requests), has one session's
transition commit first, then proves the second session's transition — attempted with the
status it observed *before* the first session's commit — correctly fails instead of
silently succeeding a second time.
