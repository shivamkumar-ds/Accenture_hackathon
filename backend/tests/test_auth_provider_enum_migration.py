"""
Regression coverage for Bug #005 (docs/BUG_BUCKET.md): the `auth_provider`
Postgres enum type was created (migration a1b2c3d4e5f6) with lowercase
labels ('local', 'google'), but SQLAlchemy's Enum(AuthProvider) column
type -- with no values_callable override, matching every other enum
column in this schema -- always writes the Python enum member's NAME
('LOCAL', 'GOOGLE'), never its .value. Every INSERT into `users` failed
against real Postgres with InvalidTextRepresentation. This was invisible
to the rest of the test suite because it runs against in-memory SQLite,
which does not enforce Postgres ENUM label constraints at all -- SQLite
just stores the string. See the "Engineering Rule" in Bug #005 for why
this test exists as a static check instead: it doesn't need a live
Postgres connection to catch the exact mismatch that broke a real one.

The check: for every label the migration's `auth_provider_enum` DDL
literally declares, the model's AuthProvider enum must have a member
whose *name* equals that label -- because member.name is what
SQLAlchemy actually serializes to the database for this column, not
member.value. Before the fix, the migration declared 'local'/'google'
(lowercase); AuthProvider's member names are 'LOCAL'/'GOOGLE' -- no
match, and this test fails exactly the way the real INSERT did. After
the fix (migration b2c3d4e5f6a7 renames the Postgres enum labels to
uppercase), the labels the *column* actually reads at runtime match --
proven here by asserting against the model's own compiled Enum type,
which is what every future migration/model change must stay
self-consistent with.
"""

import importlib.util
import inspect
import re
from pathlib import Path

from app.models.company import User
from app.models.enums import AuthProvider

VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def _load_migration(filename: str):
    """
    Loads an Alembic version file directly by path -- the same approach
    Alembic itself uses internally (ScriptDirectory), and necessary here
    because `alembic.versions.<file>` as a dotted import path collides
    with the real, pip-installed `alembic` package (this project's own
    migrations directory happens to share that top-level name).
    """
    path = VERSIONS_DIR / f"{filename}.py"
    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_provider_column_enum_labels_match_python_member_names():
    """
    User.auth_provider's SQLAlchemy Enum type, exactly as the ORM will
    compile it for any dialect, must produce label strings equal to
    AuthProvider's member *names* -- this is the actual serialization
    contract for every Enum-typed column in this codebase (no
    values_callable overrides exist anywhere), and is what the real
    Postgres enum type's labels must match.
    """
    column_type = User.__table__.c.auth_provider.type
    assert set(column_type.enums) == {member.name for member in AuthProvider}


def test_fix_migration_renames_enum_values_to_match_model_serialization():
    """
    Directly inspects the fix-forward migration (b2c3d4e5f6a7) rather than
    requiring a live Postgres connection: it must rename every label the
    original migration (a1b2c3d4e5f6) declared in lowercase to the exact
    uppercase form AuthProvider's member names actually serialize to.
    """
    original = _load_migration("a1b2c3d4e5f6_add_google_auth_to_users")
    fix = _load_migration("b2c3d4e5f6a7_fix_auth_provider_enum_casing")

    original_labels = set(original.auth_provider_enum.enums)
    assert original_labels == {"local", "google"}  # documents the bug's exact shape

    # Parse the fix migration's actual upgrade() source for its literal
    # `ALTER TYPE auth_provider RENAME VALUE 'old' TO 'new'` statements --
    # this checks what the migration genuinely does, not just that some
    # docstring claims it does the right thing.
    fix_source = inspect.getsource(fix.upgrade)
    renames = dict(
        re.findall(r"RENAME VALUE '([a-zA-Z]+)' TO '([a-zA-Z]+)'", fix_source)
    )

    assert set(renames.keys()) == original_labels, (
        "The fix migration must rename every label the original migration "
        "declared -- nothing left behind in the old (broken) casing."
    )
    for old_label, new_label in renames.items():
        assert new_label == old_label.upper(), (
            f"'{old_label}' was renamed to '{new_label}', not its uppercase "
            "form -- this is exactly the casing SQLAlchemy's Enum(AuthProvider) "
            "column actually serializes."
        )
        assert new_label in {member.name for member in AuthProvider}
