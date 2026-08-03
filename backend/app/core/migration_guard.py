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
from sqlalchemy import create_engine

from app.core.config import Settings

logger = logging.getLogger(__name__)

# backend/app/core/migration_guard.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = BACKEND_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = BACKEND_ROOT / "alembic"


class MigrationOutOfDateError(RuntimeError):
    """The database's Alembic revision doesn't match the code's migration
    head. Raised at startup, not discovered later via a runtime query
    failure -- see module docstring."""


def _alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    return config


def get_code_head_revision() -> str | None:
    """The latest migration revision the checked-out code defines.

    None only if the alembic/versions directory has no migrations at
    all yet (not the current state of this project, but handled
    correctly rather than assumed away).
    """
    script = ScriptDirectory.from_config(_alembic_config())
    return script.get_current_head()


def get_database_revision(database_url: str) -> str | None:
    """The revision the database is actually stamped at.

    None means either a brand-new, unmigrated database, or one that
    predates Alembic being introduced to this project -- both are
    legitimately "out of date" and should surface the same message.
    """
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()


def format_out_of_date_message(current_revision: str | None, head_revision: str | None) -> str:
    """The exact developer-facing message shown on a mismatch -- large,
    unambiguous, and carrying the one command that fixes it."""
    border = "=" * 70
    return (
        f"\n{border}\n"
        "DATABASE SCHEMA OUT OF DATE\n"
        f"{border}\n\n"
        f"Database Revision:\n  {current_revision or '(no migrations applied yet)'}\n\n"
        f"Latest Revision:\n  {head_revision or '(no migrations exist)'}\n\n"
        "Run:\n\n"
        "  cd backend\n"
        "  alembic upgrade head\n\n"
        "Server startup aborted.\n"
        f"{border}\n"
    )


def check_migrations_current(settings: Settings) -> None:
    """
    Compare the database's current Alembic revision against the code's
    migration head.

    Raises MigrationOutOfDateError on a mismatch. Callers decide what
    "fatal" means for their environment (see main.py's lifespan
    handler and Settings.migration_guard_fail_on_mismatch) -- this
    function's only job is detection and a clear message, not deciding
    whether to take the process down.
    """
    head_revision = get_code_head_revision()
    current_revision = get_database_revision(settings.database_url)

    if current_revision == head_revision:
        logger.info("Database schema is up to date (revision=%s).", current_revision)
        return

    message = format_out_of_date_message(current_revision, head_revision)
    logger.error(message)
    raise MigrationOutOfDateError(message)
