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

### Closure

Closed 4 August 2026 after a founder final review confirmed the subsystem covers: stale
schemas, unmigrated databases, diverged migration histories, and a codebase with zero
migration files — each with a clear, developer-facing message and a passing regression
test (`backend/tests/test_migration_guard.py`, 5 tests). No revision ID is hardcoded
anywhere in the implementation. This subsystem is now considered permanent infrastructure;
per the Bug Lifecycle above, it does not require further architectural work unless a real
production issue is found.
