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
