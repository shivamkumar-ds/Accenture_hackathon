"""
Permanent database migration safety system.

See docs/BUG_BUCKET.md Bug #001 for the incident this exists to prevent:
on 4 August 2026, the backend was started against a local Postgres
database that hadn't had a just-added migration (the `category` column
on `tenders`) applied yet. The code and schema silently drifted apart,
and every query touching the changed table failed with a raw
`psycopg2.errors.UndefinedColumn` deep inside a stack trace -- a
runtime 500, discovered by clicking around the app, not a clear signal
at the moment the mismatch was introduced.

Engineering rule (binding going forward): a migration mismatch is a
fatal *startup* error, never a runtime error. A developer should find
out the instant they start the server, not after navigating into the
one screen whose query happens to touch the changed table.

Generic by construction -- this reads the database's current revision
and the code's migration head entirely through Alembic's own APIs
(ScriptDirectory, MigrationContext). No revision ID is ever hardcoded
here, so it works unmodified for every migration that gets added after
this one, with zero manual maintenance.
"""

import logging
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError

from app.core.database import engine

logger = logging.getLogger(__name__)

# backend/app/core/migration_guard.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = BACKEND_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = BACKEND_ROOT / "alembic"


class MigrationOutOfDateError(RuntimeError):
    """The database's Alembic revision doesn't match the code's migration
    head (or the migration history itself is ambiguous -- see
    get_code_head_revision). Raised at startup, not discovered later via
    a runtime query failure -- see module docstring."""


def _alembic_config() -> AlembicConfig:
    """A minimal AlembicConfig for reading migration script metadata only
    -- this never connects to a database (unlike alembic/env.py's own
    Config, used when running the `alembic` CLI), so it never touches
    sqlalchemy.url.

    script_location is overridden with an absolute path rather than
    trusting alembic.ini's own `script_location = alembic` as-is:
    Alembic resolves a relative script_location against the process's
    current working directory, not the .ini file's directory. The CLI
    happens to always be run from backend/, so that relative path works
    there, but this module runs as part of the app importing normally
    (e.g. under uvicorn), where the working directory isn't guaranteed
    to be backend/. Passing an absolute path removes that assumption
    entirely.
    """
    config = AlembicConfig(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    return config


def get_code_head_revision() -> str:
    """The latest migration revision the checked-out code defines.

    Raises MigrationOutOfDateError (rather than a raw alembic
    CommandError) if the migration history has more than one head --
    e.g. two branches each added a migration without a merge revision
    reconciling them. That's a broken/ambiguous migration history, not
    a normal "just run upgrade head" situation, but it should still
    fail startup with the same clear, developer-facing message format
    as every other case this module handles, not a bare stack trace
    from a different exception type.
    """
    script = ScriptDirectory.from_config(_alembic_config())
    try:
        head = script.get_current_head()
    except CommandError as exc:
        raise MigrationOutOfDateError(
            f"Could not determine a single migration head: {exc}\n"
            "This usually means the migration history has diverged "
            "(multiple heads). Run `alembic heads` in backend/ to see "
            "them, then `alembic merge` to reconcile before starting "
            "the server."
        ) from exc
    if head is None:
        raise MigrationOutOfDateError(
            "No Alembic migrations found under alembic/versions/ -- "
            "this project should always have at least one."
        )
    return head


def get_database_revision() -> str | None:
    """The revision the database is actually stamped at.

    Reuses the app's single shared engine (app.core.database.engine)
    rather than opening a second, throwaway connection pool just for
    this check -- one engine per process, same as everywhere else in
    the codebase.

    None means either a brand-new, unmigrated database, or one that
    predates Alembic being introduced to this project -- both are
    legitimately "out of date" and surface the same message.

    A connection failure (e.g. Postgres isn't running at all) is
    deliberately left uncaught here: that's a different, more basic
    problem than a schema mismatch, and the resulting exception
    already explains itself clearly without this module dressing it
    up as something it isn't.
    """
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def format_out_of_date_message(current_revision: str | None, head_revision: str) -> str:
    """The exact developer-facing message shown on a mismatch -- large,
    unambiguous, and carrying the one command that fixes it."""
    border = "=" * 70
    return (
        f"\n{border}\n"
        "DATABASE SCHEMA OUT OF DATE\n"
        f"{border}\n\n"
        f"Database Revision:\n  {current_revision or '(no migrations applied yet)'}\n\n"
        f"Latest Revision:\n  {head_revision}\n\n"
        "Run:\n\n"
        "  cd backend\n"
        "  alembic upgrade head\n\n"
        "Server startup aborted.\n"
        f"{border}\n"
    )


def check_migrations_current() -> None:
    """
    Compare the database's current Alembic revision against the code's
    migration head.

    Raises MigrationOutOfDateError on a mismatch (or an ambiguous
    migration history -- see get_code_head_revision). Callers decide
    what "fatal" means for their environment (see main.py's lifespan
    handler and Settings.migration_guard_fail_on_mismatch) -- this
    function's only job is detection and a clear message, not deciding
    whether to take the process down.
    """
    head_revision = get_code_head_revision()
    current_revision = get_database_revision()

    if current_revision == head_revision:
        logger.info("Database schema is up to date (revision=%s).", current_revision)
        return

    message = format_out_of_date_message(current_revision, head_revision)
    logger.error(message)
    raise MigrationOutOfDateError(message)
