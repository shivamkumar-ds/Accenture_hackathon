"""fix auth_provider enum casing (Bug #005)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-13 23:00:00.000000

Migration a1b2c3d4e5f6 created the `auth_provider` Postgres enum type with
lowercase labels ('local', 'google') -- inconsistent with every other enum
column in this schema (user_role, user_status, document_processing_status,
etc.), all of which use the Python enum member's NAME (uppercase --
'ADMINISTRATOR', 'ACTIVE', 'PENDING', ...), because SQLAlchemy's
Enum(SomePythonEnum) column type serializes using `.name`, not `.value`,
with no values_callable override anywhere in this codebase. The mismatch
made every INSERT into `users` fail with
`psycopg2.errors.InvalidTextRepresentation: invalid input value for enum
auth_provider: "LOCAL"` -- see docs/BUG_BUCKET.md Bug #005.

Fix-forward, not a rewrite of a1b2c3d4e5f6 -- per the project's own rule
that Alembic history stays authoritative once a migration may have been
applied. `ALTER TYPE ... RENAME VALUE` (Postgres 10+) renames the enum
labels in place; every existing row's value is transparently renamed
along with it (there are no rows with this column populated yet in any
real deployment, but the operation is safe regardless).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE auth_provider RENAME VALUE 'local' TO 'LOCAL'")
    op.execute("ALTER TYPE auth_provider RENAME VALUE 'google' TO 'GOOGLE'")
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider SET DEFAULT 'LOCAL'")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider SET DEFAULT 'local'")
    op.execute("ALTER TYPE auth_provider RENAME VALUE 'GOOGLE' TO 'google'")
    op.execute("ALTER TYPE auth_provider RENAME VALUE 'LOCAL' TO 'local'")
