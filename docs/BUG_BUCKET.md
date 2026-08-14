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

---

## Bug #004

**Title:** `record_decision()` could write a misleading "Decision recorded" audit entry
before the mission's status change was actually committed

**Status:** Closed — 4 August 2026

**Date:** 4 August 2026

**Severity:** Medium (data-integrity/audit-trail correctness — found during the Phase 1
Backend Stabilization Audit's Compliance/Approval review, not reported by a user; directly
relevant because the product's core value proposition is an auditable, explainable
decision trail)

**Category:** Backend / Transaction ordering

### Symptoms (would-be, if triggered)

None observed in production. Found by review: `approval_service.record_decision()` called
`_log(...)` — which writes an `AuditLog` row and commits it immediately — *before* applying
and committing the mission's own status change (`mission.status = COMPLETED`, `completed_at
= now()`). If that second, later commit had ever failed (a dropped connection, a transient
`OperationalError`), the AuditLog would already show "Decision recorded: PROCEED" while the
mission itself silently remained `AWAITING_APPROVAL` — a permanent, false record of a
business decision that never actually took effect.

### Root Cause

Two independent commits inside one logical operation, in the wrong order: the "fact" (audit
log entry) was persisted before the "truth" (the actual state change) was confirmed
persisted. `approval_service.verify_compliance_row()`, right above this function in the same
file, already gets this ordering right — it commits the real row mutation first and only
logs afterward — so this was an inconsistency with the file's own established, safer
pattern, not a novel design question.

### Fix

`backend/app/services/approval_service.py::record_decision()` — reordered so the mission's
own `db.commit()` happens first; `_log(...)` (and its own commit) now only runs once that
has already succeeded.

### Prevention

Matches the ordering already used by `verify_compliance_row()` in the same module — any
future function following that established pattern (commit the real change, then log it)
is safe by construction; a reviewer comparing new code against the existing functions in
this file will see the correct order modeled twice now, not once.

### Engineering Rule

**An audit-trail write must never commit before the fact it's recording has itself been
durably committed.** Where a single logical operation involves both a state change and a
log entry describing it, the state change's commit must happen first — a log entry is a
claim about something that already happened, never a claim about something about to happen.

### Regression tests

`backend/tests/test_approval_decision_audit_ordering.py` —
`test_failed_mission_commit_leaves_no_misleading_audit_entry`: forces the mission-state
commit to fail and asserts no `AuditLog` row was written and the mission's status is
unchanged — proving the audit trail can no longer claim a decision that didn't happen.

---

## Phase 1 Backend Stabilization Audit — Areas Reviewed, No Bug Found

Documented per the audit's explicit "state it, don't invent work" instruction. Each area
below was read in full and checked against: CRUD correctness, exception handling,
transaction boundaries, rollback behaviour, validation, ownership/company-scoping,
soft-delete conventions, null handling, duplicate handling, and (where applicable) race
conditions.

- **`document_service.py`** — upload/list/get/delete. Transaction boundaries correct
  (upload rolls back and unlinks the on-disk file together on failure); delete is
  soft-delete only and correctly blocked by `ConflictError` while any active Tender or
  capability entity still references the document. No changes made.
- **`capability_service.py`** — build/list/find/update/soft-remove. Duplicate-build
  guard (`document_has_active_capabilities`) checked before extraction starts, not after;
  the one `db.commit()` mid-function (setting `PROCESSING`) is intentionally followed by
  its own dedicated try/except around the extraction call, same shape as the tender
  analysis fix above, and was already correct here. No changes made.
- **`auth_service.py` / `company_service.py` / `user_service.py`** — registration is
  atomic (Company + first Administrator, one transaction, `IntegrityError` mapped to a
  clean `ConflictError` either way); login returns an identical error message for "no such
  user" and "wrong password" (no account-enumeration leak); rate limiting is in place on
  both `/auth/register` and `/auth/login`. No changes made.
- **`decision_service.py::run_evaluation()`** — every DB write (`CapabilitySnapshot`,
  `Recommendation`, `CapabilityMapping`, `ComplianceMatrix`, the final `Mission` update)
  happens via `db.flush()` (to obtain FK-able IDs) with a single `db.commit()` at the very
  end; an exception anywhere in the reasoning or write sequence leaves nothing committed,
  and `app/core/database.py::get_db()`'s `finally: db.close()` implicitly rolls back
  whatever was never committed — so a mid-function failure can never leave a partial
  evaluation persisted. Also specifically checked: `matched_entity_id` is only ever set
  from an LLM-returned index that's bounds-checked against the real candidate list
  (`app/agents/decision_engine.py`), so the later `next(e for t, e in candidates if e.id ==
  result.matched_entity_id)` lookup in `decision_service.py` can never raise
  `StopIteration` from a hallucinated ID — genuinely unreachable, not just unlikely. No
  changes made.
- **Reports / PDF export** — this backend has no PDF/report-generation module or endpoint.
  The standalone `Reports.tsx` frontend page and its route were already retired earlier in
  this project (frontend is feature-frozen); reporting is served entirely through the
  existing `/evaluation` and `/approval` JSON APIs the Decision/Evidence screens already
  consume. Nothing to audit here — confirmed absent, not skipped.

---

## Bug #005

**Title:** `auth_provider` Postgres enum type created with the wrong casing — every user
registration/login failed against a real database

**Status:** Closed — 13 August 2026

**Date:** 13 August 2026

**Severity:** Critical (blocks every registration and login — the entire product is
unusable)

**Category:** Backend / Database migration

### Symptoms

- Registration ("Create your workspace") and login both failed in the frontend with a
  generic `Network Error` toast — no distinguishable HTTP error surfaced to the user.
- The actual backend exception, visible only in the server terminal:
  `sqlalchemy.exc.DataError: (psycopg2.errors.InvalidTextRepresentation) invalid input
  value for enum auth_provider: "LOCAL"`, raised on every `INSERT INTO users`.
- This was reported as a suspected network/connectivity issue (a genuinely reasonable
  first read of "Network Error" from the frontend) and investigated as one first, per the
  project's engineering rule — see "How this was investigated" below.

### Root Cause

The `auth_provider` Postgres enum type was created (migration `a1b2c3d4e5f6`, Phase 2:
Google Authentication) with **lowercase** labels: `sa.Enum('local', 'google',
name='auth_provider')`. Every other enum column in this schema — `user_role`,
`user_status`, `document_processing_status`, `mission_status`, and the rest, all defined
in the original `3d8622ed98f0` schema migration — uses **uppercase** labels matching the
Python enum member's `.name` (`'ADMINISTRATOR'`, `'ACTIVE'`, `'PENDING'`, ...), because
SQLAlchemy's `Enum(SomePythonEnum)` column type, with no `values_callable` override
anywhere in this codebase, always serializes using `.name`, never `.value`. `AuthProvider`
was defined the same way as every other enum (`LOCAL = "local"`, `GOOGLE = "google"`), so
the ORM tried to write `'LOCAL'` — a label that simply did not exist in the Postgres type,
which only had `'local'`/`'google'`. Postgres correctly rejected the insert.

This is a pure casing mismatch introduced by not following the established (if implicit)
convention already present everywhere else in the schema — not a logic error, not a
concurrency issue, not related to migration guard, storage, or anything else touched
during Phase 3.

### How this was investigated

The founder's report was "Network Error" on submit, with no assumption from either side
about frontend vs. backend. Investigation order, per the engineering rule (reproduce
before fixing):
1. Ruled out the LLM/Vertex AI configuration in the founder's local `.env`
   (`GEMINI_AUTH_MODE=vertex`) as a red herring — confirmed `get_llm_client()` only
   constructs a client for whichever provider `LLM_PROVIDER` actually selects (`openai`
   in this case), and neither `/auth/register` nor `/auth/login` ever calls the LLM client
   at all.
2. Requested the actual backend terminal output rather than guessing further — "Network
   Error" alone is consistent with several genuinely different causes (backend not
   running, a CORS origin mismatch, or a crash), and only the real evidence could
   distinguish between them.
3. The founder's terminal output contained the full traceback and the exact failing SQL
   statement with its bound parameters (`'auth_provider': 'LOCAL'`) — this is what made
   the root cause certain rather than inferred.
4. Cross-checked every other enum column's migration DDL against this one and found the
   casing convention this migration broke, confirming *why* this specific column failed
   and no others ever had.

### Fix

New migration `b2c3d4e5f6a7` (fix-forward, not an edit to the already-applied
`a1b2c3d4e5f6` — per the standing rule that Alembic history stays authoritative once a
migration may have been applied by anyone): `ALTER TYPE auth_provider RENAME VALUE 'local'
TO 'LOCAL'` and `... 'google' TO 'GOOGLE'`, plus resetting the column's `SET DEFAULT` to
match. Running `alembic upgrade head` again applies this on top of the already-migrated
local database.

### Prevention

`backend/tests/test_auth_provider_enum_migration.py` — two tests. The first asserts the
model's own compiled `Enum` type produces exactly the label set `AuthProvider`'s member
*names* would produce (the actual, permanent serialization contract for this and every
other enum column here). The second directly inspects the fix migration's source for its
literal `RENAME VALUE` statements and asserts every one renames to the correct uppercase
form. Neither requires a live Postgres connection — see the Engineering Rule below for why
that matters.

### Engineering Rule

**A Postgres-backed `Enum` column's migration-declared labels must always be the Python
enum class's member *names*, in the exact casing they appear in code — never hand-typed,
never the member's `.value`.** This project has no `values_callable` override anywhere, so
`.name` is always what gets written; a migration that types out labels by hand (as opposed
to deriving them, e.g. via `[m.name for m in SomeEnum]`) can silently diverge from that,
and — critically — **this class of bug is invisible to this project's entire test suite**,
because every other test runs against in-memory SQLite, which stores enum-typed columns as
plain strings and never enforces Postgres's `CREATE TYPE ... AS ENUM` label constraint at
all. `test_auth_provider_enum_migration.py`'s pattern (assert the model's compiled label
set, then statically inspect any migration that hand-types enum DDL) is the template for
catching this class of bug for any future Postgres-backed enum column, without needing a
live Postgres connection to do it.

### Closure

Closed 13 August 2026. Verified: full backend suite (41/41, including the new tests)
passing, single linear Alembic head (`b2c3d4e5f6a7`) confirmed via `alembic history`, fix
migration reviewed against every other existing enum migration in the schema to confirm no
other column shares this defect.

---

## Bug #006

**Title:** `contact_submissions` migration raised `DuplicateObject` against real PostgreSQL
— a second, unnecessary `CREATE TYPE` for an enum shared by two columns

**Status:** Closed — 14 August 2026

**Date:** 14 August 2026

**Severity:** High (blocks the Contact Form Backend feature from ever reaching a real
database — the migration cannot apply, so the feature is entirely unusable outside the
SQLite-based test suite)

**Category:** Backend / Database migration

### Symptoms

- Local verification (per the founder's own real local-Postgres testing pass, done
  deliberately before any GCP work) ran `alembic upgrade head` to apply migration
  `c3d4e5f6a7b8` ("add contact_submissions table"). It failed with:
  `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) type
  "contact_email_status" already exists`, on the `CREATE TYPE contact_email_status AS ENUM
  ('PENDING', 'SENT', 'FAILED')` statement, raised from inside `op.create_table(...)` — not
  from the migration's own earlier, explicit type-creation line.
- Alembic reported `Will assume transactional DDL` before running the migration, and
  PostgreSQL's transactional DDL held: the entire migration (including the type this
  migration had already successfully created moments earlier, in the same transaction)
  rolled back cleanly on the error. The founder's database remained exactly at its prior
  revision, `b2c3d4e5f6a7` — confirmed via `alembic current` before and after the failed
  attempt. No partial schema, no orphaned type, no manual cleanup was ever required.

### Root Cause

The migration explicitly pre-creates the `contact_email_status` Postgres enum type once
(`contact_email_status_enum.create(op.get_bind(), checkfirst=True)`), because the type is
shared by two columns (`notification_status`, `confirmation_status`) on the
`contact_submissions` table created in the same `op.create_table(...)` call. Each column's
type was then declared as its own, separately-constructed **generic** `sa.Enum('PENDING',
'SENT', 'FAILED', name='contact_email_status', create_type=False)`.

`create_type=False` is supposed to stop SQLAlchemy from re-issuing `CREATE TYPE` when a
column referencing that type is itself created. In SQLAlchemy 2.0.35 (the version pinned in
`requirements.txt`), that flag does not reliably survive the adaptation of a *generic*
`sa.Enum` into the Postgres-dialect-specific `ENUM` implementation that actually handles DDL
dispatch during `op.create_table()`. Each of the two separately-constructed generic `Enum`
objects was adapted into its own new dialect-impl object at DDL-compile time, and
SQLAlchemy's per-DDL-run de-duplication memo (`NamedType._check_for_name_in_memos`, which is
what would otherwise recognize "this named type was already created earlier in this same
statement") only works when the *same* type object is reused — with two distinct objects,
the memo never linked them, and the DDL visitor issued `CREATE TYPE` again during
`create_table`, colliding with the type this migration had already created moments earlier
in the same open transaction.

This is not a logic error in the application code, not related to Bug #001 or Bug #005, and
does not affect any other migration in the schema — every other Postgres enum type in this
project (`user_role`, `user_status`, `auth_provider`, etc.) is used by exactly one column, so
this specific "one type, two columns, one `create_table`" sharing pattern had never been
exercised before this migration.

### Why SQLite-based tests did not catch it

Every test in this suite runs against in-memory SQLite (`sqlite:///:memory:`), which has no
`CREATE TYPE` / native enum concept at all — SQLAlchemy stores an `Enum`-typed column as a
plain `VARCHAR` with a `CHECK` constraint against SQLite, never emitting anything resembling
Postgres's named-type DDL. A test suite that only ever runs against SQLite is structurally
incapable of reproducing this failure, regardless of how thorough it is — the same blind spot
already documented in Bug #005's Engineering Rule, now confirmed a second time by a distinct
bug in the same class of code (Postgres-specific enum DDL).

### Fix

Same migration file (`c3d4e5f6a7b8_add_contact_submissions.py`), corrected in place — not a
new migration, since this one had never successfully applied to any real database (the
founder's local Postgres included). Two changes:

1. `contact_email_status_enum` is now constructed once, at module level, using
   `sqlalchemy.dialects.postgresql.ENUM` (the dialect-specific class) rather than generic
   `sa.Enum`.
2. That exact same object is reused for the explicit `.create()` call, the
   `notification_status` column, and the `confirmation_status` column — never
   re-constructed. `downgrade()` reuses it too for the final `.drop()` call, after
   `drop_table` (Postgres refuses to drop a type still referenced by a table's column, so the
   table must go first).

This is the pattern SQLAlchemy's own documentation recommends for "one named Postgres enum
type shared by multiple columns created in the same `op.create_table()`."

### Prevention

`backend/tests/test_contact_submissions_enum_migration.py` — three tests, statically
inspecting the migration's actual source (the same technique
`test_auth_provider_enum_migration.py` uses for Bug #005, since neither bug can be
reproduced against SQLite): (1) `contact_email_status_enum` is genuinely a
`postgresql.ENUM` instance with `create_type=False`, not a generic `sa.Enum`; (2)
`upgrade()`'s source contains no inline `sa.Enum(...)`/`postgresql.ENUM(...)` construction
anywhere, and references the shared `contact_email_status_enum` object at least three times
(the explicit `create()` call plus both columns); (3) `downgrade()` drops the table before
dropping the enum type.

**Explicit limitation, stated plainly:** these are structural/static checks, not a live
PostgreSQL execution of the migration. This environment has no PostgreSQL instance available
(no root/sudo, no Docker — the same constraint documented in Bug #005), so nothing in this
repository's automated test suite can execute `CREATE TYPE`/`op.create_table` DDL against a
real Postgres server and directly prove the fix works end-to-end. That proof is the
founder's own `alembic upgrade head` run against their real local PostgreSQL database — see
Verification below.

### Engineering Rule

**When a single named Postgres enum type is shared by more than one column (or an explicit
`.create()`/`.drop()` call) within the same migration, construct exactly one
`sqlalchemy.dialects.postgresql.ENUM(..., create_type=False)` object and reference that same
object everywhere the type is needed.** Never construct a second `sa.Enum(...)` or
`postgresql.ENUM(...)` for the same Postgres type name, even with `create_type=False` set —
generic `sa.Enum`'s `create_type` flag is not guaranteed to survive dialect adaptation during
`op.create_table()`'s DDL dispatch, and even the dialect-specific class relies on SQLAlchemy
recognizing it as *the same object already handled* within one DDL run, which only works
when it genuinely is the same object. This is a distinct lesson from Bug #005 (label casing)
— both are "Postgres enum DDL is stricter than SQLite lets a test suite notice," but this one
is about object identity/DDL de-duplication, not label values.

### Verification

Structural: `test_contact_submissions_enum_migration.py`'s three new tests pass, alongside
the full existing backend suite (SQLite-based — see the stated limitation above). Migration
structure re-inspected by hand against the fix's own stated requirements (one shared object,
no inline reconstruction, table dropped before type).

**Verified against real PostgreSQL.** The founder ran `alembic upgrade head` against their
actual local database:

```
INFO  [alembic.runtime.migration] Running upgrade b2c3d4e5f6a7 -> c3d4e5f6a7b8, add contact_submissions table (Contact Form Backend)
```

No error, no traceback — the migration that previously failed with `DuplicateObject` applied
cleanly on the corrected version. This is the actual proof the fix works, independent of and
in addition to the structural regression tests above.

### Closure

Closed 14 August 2026. Migration fixed, regression-tested (structurally, with the SQLite
limitation stated explicitly), and confirmed applying cleanly against a real local
PostgreSQL database.

## Bug #007

**Title:** Tender could only ever have one source document, and only PDF was accepted —
a real CPPP government tender (main PDF + technical bid spreadsheet + financial BOQ
spreadsheet) could not be represented or analyzed at all

**Status:** Fixed — 15 August 2026 (pending the founder's own local validation against the
real three-file tender, same closure pattern as Bug #006)

**Date:** 15 August 2026

**Severity:** High (product-defining limitation, not a peripheral bug — real-world
procurement tenders routinely ship as a main tender document plus one or more spreadsheet
attachments, e.g. a technical bid detail sheet and a financial Bill of Quantities. A
platform that can only accept a single PDF per tender cannot evaluate this entire, common
class of real tenders at all)

**Category:** Backend / Product architecture (Tender ↔ Document data model, document
parsing, tender analysis pipeline) + Frontend (Tender Workspace)

### Symptoms

- Discovered during local customer-journey validation (per the founder's own Master
  Launch Control plan) using an actual, real CPPP (Indian government e-procurement)
  tender: `tender.pdf` (main tender document), `tech.xls` (technical bid detail), and
  `BOQ_969057.xls` (financial Bill of Quantities) — three files that all genuinely belong
  to the same tender.
- `Tender.uploaded_document` was a single, nullable foreign key to one `Document` row —
  there was no schema-level way to attach a second document to an existing Tender at all.
- `app/core/storage.py`'s `ALLOWED_EXTENSIONS`/`ALLOWED_CONTENT_TYPES` only recognized
  `.pdf`/`.docx`/`.png`/`.jpg`/`.jpeg` — any `.xls`/`.xlsx` upload was rejected outright
  with `UnsupportedFileTypeError` before ever reaching the analysis pipeline.
- `app/agents/document_parser.py` had no spreadsheet extraction path at all.
- `app/agents/tender_analyzer.py`'s `analyze_tender()` took exactly one `Path` and called
  `extract_pdf_pages()` on it — structurally incapable of combining more than one source
  document into a single extraction run, even if the schema had allowed attaching one.

This was not a data-corruption or crash bug — the existing single-PDF flow worked exactly
as designed. It is a genuine, pre-existing product capability gap: the product's data
model and pipeline were built around an assumption ("one tender = one PDF") that does not
hold for a real, common class of tenders. Not a newly introduced defect from this session's
other work.

### Root Cause

The Tender ↔ Document relationship was modeled as a single nullable FK
(`Tender.uploaded_document`) from the earliest schema design onward, and every downstream
consumer (`tender_service.run_analysis()`, `tender_analyzer.analyze_tender()`,
`document_parser.extract_text()`'s format dispatch, `storage.ALLOWED_EXTENSIONS`) was built
to match that one-document, PDF-only assumption. Nothing in the architecture was wrong for
the tenders it was tested against during development — the gap only became visible against
a real government tender bundle, which is exactly why the founder's "validate with a real
external tender before declaring the product done" step in the Master Launch Control plan
exists.

### Why the existing (SQLite-based) test suite did not catch it

This was a missing-capability gap, not a behavioral bug in existing code — no test could
have caught it because there was no code path to attach a second document to a Tender or
to parse a spreadsheet at all. SQLite vs. PostgreSQL is not the relevant distinction here
(unlike Bugs #005/#006); the gap was in the product's schema and pipeline design, equally
absent in every environment.

### Fix

Implemented the general solution the founder explicitly required — ONE TENDER → MULTIPLE
SOURCE DOCUMENTS → MULTIPLE SUPPORTED FORMATS → ONE REQUIREMENT/DECISION PIPELINE, not a
special case for this one tender:

- **Schema** (migration `d4e5f6a7b8c9`, additive/nullable only): `documents.tender_id` +
  `documents.document_role` (the general Tender↔Document relationship, replacing the
  implicit single-document assumption); `requirements.source_document_id` +
  `requirements.source_location` (format-agnostic provenance, e.g. `"Sheet: Sheet1"`,
  alongside the existing `source_page`, unchanged in meaning for PDF-sourced requirements).
  A backfill UPDATE links every pre-existing Tender's Document via the new columns so no
  special-case fallback code is ever needed for old data.
- **File format support**: `openpyxl` (`.xlsx`) and `xlrd` (`.xls`, openpyxl cannot read
  the legacy binary format at all) added to `document_parser.py`'s
  `extract_spreadsheet_sheets()` — row/column structure preserved as `"cell | cell"` lines
  per sheet, empty sheets and rows dropped, never a binary/raw dump.
- **Storage allowlist**: `.xls`/`.xlsx` added to `storage.ALLOWED_EXTENSIONS`, with a
  scoped content-type leniency for `application/octet-stream` (real CPPP/GeM portals
  routinely serve spreadsheet attachments with this generic content-type rather than the
  correct MIME type — confirmed against the actual tender files this fix was built
  against).
- **Analysis pipeline**: `tender_analyzer.analyze_tender()` generalized to accept a list of
  `TenderSourceDocument`s. Every non-financial-role document's content (PDF pages or
  spreadsheet sheets alike) is flattened into one ordered sequence of `SourceUnit`s and fed
  through the *exact same* chunking / `[PAGE N]`-marker / LLM-prompt mechanism that already
  existed for PDF-only tenders — `prompts/tender_requirement.py`, `schemas/extraction.py`,
  and `mock_extraction.py` needed zero changes as a result. Financial/BOQ-role documents
  are excluded from LLM input by a simple deterministic filter (not a second AI call) since
  pricing line items are not tender requirements. `tender_service.run_analysis()` now
  gathers every `Document` attached via `tender_id` (via `contextlib.ExitStack`, so a
  GCS-backed tender can hold several documents' temp files open for one analysis run) in
  place of the single `uploaded_document` lookup.
- **API**: new `POST /tenders/{tender_id}/documents` (reuses
  `document_service.upload_document()`'s validation/storage path — same allowlist, same
  size limit); `GET /tenders/{tender_id}` and `POST /analysis/run` now also return the
  attached `documents` list. No new DELETE endpoint — the existing
  `DELETE /documents/{id}` was generalized (its blocking-tender check now also covers
  `Document.tender_id`, not just the legacy `uploaded_document`) and reused.
- **Document roles**: inferred from filename when not explicitly supplied
  (`boq`/`financial`/`price`/`commercial` → financial, `tech` → technical,
  `annex`/`supporting` → annexure, else → annexure), matching `Tender.category`'s existing
  plain-string convention rather than a new enum.
- **Frontend**: a "Tender Documents" card on the Tender Workspace (`Evaluation.tsx`) lists
  every attached document with a role badge and an "Add document" control (PDF/XLS/XLSX),
  matching the existing card visual language — no redesign of the frozen page structure.

### Backward compatibility

Verified explicitly, not assumed: a Tender with exactly one PDF and no other documents
produces byte-identical `source_page` values to the pre-existing single-document behavior
(`test_pdf_only_tender_analysis_unchanged`); the existing Bug #002 regression test
(`test_tender_analysis_failure_modes.py`) and every other pre-existing tender/document test
still pass unchanged.

### Prevention / Regression coverage

`backend/tests/test_tender_multi_document.py` — 19 tests, using real PDF (via `reportlab`)
and real `.xlsx` (via `openpyxl`) files on disk plus `provider="mock"`
(`app/agents/mock_extraction.py`) rather than a real LLM call, driving the actual
`tender_analyzer`/`tender_service`/`document_service`/`storage` code: PDF-only backward
compatibility, `upload_tender()` linking the new relationship, XLS/XLSX accepted (including
the octet-stream leniency), unsupported extensions still rejected, spreadsheet parsing
(single sheet, multiple sheets, empty sheet dropped), combined PDF+spreadsheet extraction
with correct per-requirement source-document/source-location traceability, financial-role
document exclusion from LLM input, multi-document attachment with filename-based and
explicit role assignment, company isolation on the new document-list/add-document paths,
and the generalized document-deletion blocking check. All in-memory SQLite (this project's
standing convention) — nothing in this feature depends on PostgreSQL-specific behavior, so
(unlike Bugs #005/#006) there is no stated SQLite limitation here.

### Engineering Rule

**When a product's data model encodes a cardinality assumption ("one X has exactly one
Y") that reflects the sample data used during development rather than a genuine business
rule, that assumption will eventually meet real-world data that violates it.** The fix here
generalized the schema (nullable, additive columns — no breaking change) and threaded the
same generalization through every layer (storage → parser → analyzer → service → API →
frontend) rather than special-casing the one real tender that exposed the gap — per the
founder's explicit standing instruction to implement the general solution, not a workaround.

### Verification

Full backend test suite (87 passing, excluding the pre-existing unrelated SOCKS-proxy
sandbox artifact in `tests/agents/test_llm_client.py`), `alembic heads` confirms a single
head (`d4e5f6a7b8c9`), `app.main:app` imports cleanly, frontend `tsc --noEmit` and
`vite build` both clean. **Pending**: the founder's own local run against the actual
`tender.pdf` + `tech.xls` + `BOQ_969057.xls` files (Section 7 of the governing spec) — this
entry will be updated with that real-file confirmation, the same closure pattern used for
Bug #006.

### Closure

Not yet closed — awaiting the founder's real-tender validation run and explicit
confirmation, per the standing Bug Bucket lifecycle rule that a fix is not "closed" until
verified against the actual environment/data it was built for.
