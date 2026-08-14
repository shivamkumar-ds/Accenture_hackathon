"""add contact_submissions table (Contact Form Backend)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-14 00:00:00.000000

Adds the durable store behind the landing page's Contact Us form (see the
"Decision — Proceed With Contact Form Backend" spec and
app/models/contact.py's module docstring). Standalone table, no foreign
keys into the Company/User graph -- an anonymous visitor submitting this
form is by definition not yet scoped to a company.

Enum labels are declared uppercase ('PENDING', 'SENT', 'FAILED'),
matching ContactEmailStatus's member *names* -- not repeating Bug #005
(docs/BUG_BUCKET.md), where the auth_provider enum was created with
lowercase labels while SQLAlchemy's Enum(SomePythonEnum) column type
serializes via member.name, never member.value, with no
values_callable override anywhere in this codebase.

contact_email_status is shared by two columns (notification_status,
confirmation_status) on the same table. Bug #006 (docs/BUG_BUCKET.md):
an earlier version of this migration referenced the type on each column
via two separately-constructed *generic* sa.Enum(..., create_type=False)
instances -- create_type=False did not reliably survive SQLAlchemy's
adaptation of a generic Enum into the Postgres-dialect-specific ENUM
implementation used during op.create_table()'s DDL dispatch, so the
second column's implicit "CREATE TYPE" fired anyway and collided with
the type this migration had already explicitly created a few lines
above, in the same transaction -- psycopg2.errors.DuplicateObject.

Fixed by using sqlalchemy.dialects.postgresql.ENUM (the dialect-specific
class, not generic sa.Enum) and, just as importantly, reusing the exact
same object instance for the type's one explicit `.create()` call *and*
both column definitions below -- one Python object, one Postgres type,
referenced three times, never re-constructed. This is the pattern
SQLAlchemy's own documentation recommends for "one named Postgres enum
type shared by multiple columns created in the same op.create_table()".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# One shared object, referenced everywhere below -- see Bug #006. Never
# construct a second sa.Enum/postgresql.ENUM for this same Postgres type
# name; every column that needs it must reference this exact instance.
contact_email_status_enum = postgresql.ENUM(
    'PENDING', 'SENT', 'FAILED', name='contact_email_status', create_type=False
)


def upgrade() -> None:
    contact_email_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'contact_submissions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('work_email', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('job_title', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            'notification_status',
            contact_email_status_enum,
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('notification_error', sa.Text(), nullable=True),
        sa.Column(
            'confirmation_status',
            contact_email_status_enum,
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('confirmation_error', sa.Text(), nullable=True),
    )
    op.create_index('ix_contact_submissions_work_email', 'contact_submissions', ['work_email'])
    op.create_index('ix_contact_submissions_created_at', 'contact_submissions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_contact_submissions_created_at', table_name='contact_submissions')
    op.drop_index('ix_contact_submissions_work_email', table_name='contact_submissions')
    op.drop_table('contact_submissions')
    contact_email_status_enum.drop(op.get_bind(), checkfirst=True)
