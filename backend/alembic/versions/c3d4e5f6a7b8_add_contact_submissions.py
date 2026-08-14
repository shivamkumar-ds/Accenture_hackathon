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
confirmation_status) on the same table -- the enum TYPE is created once
explicitly via .create(checkfirst=True), then both columns reference it
with create_type=False so create_table doesn't attempt to CREATE TYPE a
second time for the second column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

contact_email_status_enum = sa.Enum('PENDING', 'SENT', 'FAILED', name='contact_email_status')


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
            sa.Enum('PENDING', 'SENT', 'FAILED', name='contact_email_status', create_type=False),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('notification_error', sa.Text(), nullable=True),
        sa.Column(
            'confirmation_status',
            sa.Enum('PENDING', 'SENT', 'FAILED', name='contact_email_status', create_type=False),
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
