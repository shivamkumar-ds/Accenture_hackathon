"""
Regression test for the migration safety system (docs/BUG_BUCKET.md
Bug #001) -- codifies the Bug Lifecycle's step 7 ("Regression tested")
for this specific bug: the exact drift this guard exists to catch
(database revision != code's migration head) must always be detected
and must always raise MigrationOutOfDateError, and a database that
matches the code's head must never be flagged. Also covers the
multiple-heads edge case found during the implementation's own review.

Uses `unittest.mock.patch` rather than a real Postgres instance -- this
module's only real dependency is Alembic's own APIs (already covered
by Alembic's test suite) plus straightforward comparison logic, so a
mocked database revision is enough to exercise every branch without
requiring a live database in CI.
"""

from unittest.mock import patch

import pytest
from alembic.util.exc import CommandError

from app.core.migration_guard import (
    MigrationOutOfDateError,
    check_migrations_current,
    get_code_head_revision,
)


def test_matching_revisions_do_not_raise():
    head = get_code_head_revision()
    with patch("app.core.migration_guard.get_database_revision", return_value=head):
        check_migrations_current()  # must not raise


def test_stale_database_raises_with_actionable_message():
    with patch("app.core.migration_guard.get_database_revision", return_value="deadbeef0000"):
        with pytest.raises(MigrationOutOfDateError) as excinfo:
            check_migrations_current()

    message = str(excinfo.value)
    assert "deadbeef0000" in message
    assert get_code_head_revision() in message
    assert "alembic upgrade head" in message


def test_unmigrated_database_raises():
    """A brand-new database (no alembic_version row at all) reads as
    revision=None -- must still be treated as out of date, not as a
    false-negative match against a code head that's also somehow None."""
    with patch("app.core.migration_guard.get_database_revision", return_value=None):
        with pytest.raises(MigrationOutOfDateError) as excinfo:
            check_migrations_current()

    assert "no migrations applied yet" in str(excinfo.value)


def test_diverged_migration_history_raises_clear_error():
    """Multiple Alembic heads (e.g. two branches each added a migration
    without a merge revision) must surface the same clear,
    developer-facing error type as a normal mismatch, not a bare
    alembic.util.exc.CommandError."""
    with patch("app.core.migration_guard.ScriptDirectory") as mock_script_dir:
        mock_script_dir.from_config.return_value.get_current_head.side_effect = CommandError(
            "Multiple heads are present"
        )
        with pytest.raises(MigrationOutOfDateError) as excinfo:
            get_code_head_revision()

    assert "diverged" in str(excinfo.value) or "Multiple heads" in str(excinfo.value)


def test_no_migrations_in_codebase_raises():
    """A checkout with zero migration files (get_current_head() returns
    None, distinct from the multi-head case above) is a different kind
    of broken state -- not this project's actual condition today, but
    the code explicitly handles it, so it should be proven correct
    rather than left as an unverified branch."""
    with patch("app.core.migration_guard.ScriptDirectory") as mock_script_dir:
        mock_script_dir.from_config.return_value.get_current_head.return_value = None
        with pytest.raises(MigrationOutOfDateError) as excinfo:
            get_code_head_revision()

    assert "No Alembic migrations found" in str(excinfo.value)
