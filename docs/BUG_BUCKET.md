# Bug Bucket

A permanent, running log of every production-affecting or development-blocking bug found
in BidOps, in order — what happened, why, how it was fixed, and what now prevents the same
class of bug from recurring. This is not a task tracker; entries are never deleted, only
appended.

---

## Bug #001

**Title:** Database schema out of sync after Alembic migration

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
  (`app/core/migration_guard.py`).
- Clear, large, developer-facing error message showing both revisions and the exact fix
  command.
- Startup blocked (fatal `MigrationOutOfDateError`) when the schema is outdated, by default
  in every environment.
- `backend/README.md` updated with a "Database Migrations" section documenting the
  requirement and the guard.

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
