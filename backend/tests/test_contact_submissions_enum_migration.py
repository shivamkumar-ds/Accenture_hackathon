"""
Regression coverage for Bug #006 (docs/BUG_BUCKET.md): migration
c3d4e5f6a7b8 originally referenced the shared `contact_email_status`
Postgres enum type via two separately-constructed *generic*
sa.Enum(..., create_type=False) instances -- one per column.
create_type=False did not reliably survive SQLAlchemy's adaptation of a
generic Enum into the Postgres dialect-specific ENUM implementation used
during op.create_table()'s DDL dispatch, so the second column's implicit
"CREATE TYPE" fired anyway and collided with the type this migration had
already explicitly created a few lines earlier, in the same transaction
-- psycopg2.errors.DuplicateObject. Confirmed against a real local
PostgreSQL database (the actual bug this test guards against), not
merely reasoned about in the abstract.

IMPORTANT -- what this test can and cannot prove:
This project's test suite runs exclusively against in-memory SQLite (see
every other tests/test_*.py fixture) and has no PostgreSQL instance
available in this environment (no root/sudo, no Docker -- the same
constraint already documented in Bug #005). SQLite has no CREATE TYPE /
native enum concept at all, so it is *structurally incapable* of
reproducing this failure -- a test that merely built this table against
SQLite and asserted it worked would prove nothing about the actual bug,
and must never be represented as doing so.

What this test *can* verify without a live Postgres connection is the
exact structural property that caused the bug and that the fix
establishes: the migration must construct exactly ONE enum-type object
for `contact_email_status`, and every column that uses it (plus the
explicit create()/drop() calls) must reference that same object, never a
freshly-constructed one -- that property is what actually determines
whether SQLAlchemy emits one CREATE TYPE or two. Verified here by
parsing the migration's own source, the same technique
test_auth_provider_enum_migration.py already uses for Bug #005.

This is a real, meaningful safeguard against a regression of *this*
specific mistake, but it is not a substitute for testing against real
PostgreSQL. The actual confirmation that this bug is fixed is
`alembic upgrade head` succeeding against a real local PostgreSQL
database -- see docs/BUG_BUCKET.md Bug #006's Verification section.
"""

import importlib.util
import inspect
from pathlib import Path

from sqlalchemy.dialects.postgresql import ENUM as PostgresENUM

VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def _load_migration(filename: str):
    """Loads an Alembic version file directly by path -- necessary
    because `alembic.versions.<file>` as a dotted import path collides
    with the real, pip-installed `alembic` package (see the identical
    helper in test_auth_provider_enum_migration.py, Bug #005)."""
    path = VERSIONS_DIR / f"{filename}.py"
    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contact_email_status_enum_uses_postgres_dialect_specific_class():
    """
    The bug specifically involved a *generic* sa.Enum(...) not reliably
    honoring create_type=False once adapted to the Postgres dialect
    during DDL dispatch. The fix uses
    sqlalchemy.dialects.postgresql.ENUM directly -- assert the actual
    object's concrete type, not just that some enum-like thing exists.
    """
    migration = _load_migration("c3d4e5f6a7b8_add_contact_submissions")

    assert isinstance(migration.contact_email_status_enum, PostgresENUM)
    assert migration.contact_email_status_enum.create_type is False


def test_both_columns_and_the_explicit_create_call_share_one_enum_object():
    """
    Parses upgrade()'s actual source rather than trusting a docstring:
    the module-level `contact_email_status_enum` name must be the
    literal token used for notification_status, confirmation_status,
    AND the explicit `.create()` call -- never a second, freshly
    constructed sa.Enum(...)/postgresql.ENUM(...) built inline. This is
    exactly the property whose absence caused Bug #006: two separate
    Python objects meant SQLAlchemy's per-DDL-run "have I already
    created this type" memo (see
    sqlalchemy.dialects.postgresql.named_types.NamedType.
    _check_for_name_in_memos) never recognized the second column's type
    as the one already created, and a second CREATE TYPE was emitted.
    """
    migration = _load_migration("c3d4e5f6a7b8_add_contact_submissions")
    upgrade_source = inspect.getsource(migration.upgrade)

    assert "sa.Enum(" not in upgrade_source, (
        "upgrade() must not construct a generic sa.Enum(...) inline -- "
        "this is exactly what caused Bug #006. Reuse the module-level "
        "contact_email_status_enum object instead."
    )
    assert upgrade_source.count("postgresql.ENUM(") == 0, (
        "upgrade() must not construct a second postgresql.ENUM(...) "
        "inline -- reuse the module-level contact_email_status_enum "
        "object for every column and the explicit create() call."
    )
    assert upgrade_source.count("contact_email_status_enum") >= 3, (
        "Expected the shared contact_email_status_enum object to be "
        "referenced at least 3 times in upgrade() -- once for the "
        "explicit .create() call, once for notification_status, once "
        "for confirmation_status."
    )


def test_downgrade_drops_table_before_dropping_the_enum_type():
    """
    Postgres refuses to drop an enum type that a table's column still
    references, so the table must be dropped first. Also confirms
    downgrade() reuses the shared module-level object (not a fresh one)
    for the final .drop() call.
    """
    migration = _load_migration("c3d4e5f6a7b8_add_contact_submissions")
    downgrade_source = inspect.getsource(migration.downgrade)

    drop_table_pos = downgrade_source.find("drop_table")
    drop_enum_pos = downgrade_source.find("contact_email_status_enum.drop")
    assert drop_table_pos != -1
    assert drop_enum_pos != -1
    assert drop_table_pos < drop_enum_pos, (
        "downgrade() must drop the table before dropping the enum type "
        "it depends on."
    )
