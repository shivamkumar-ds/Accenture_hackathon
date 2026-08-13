"""add google auth fields to users

Revision ID: a1b2c3d4e5f6
Revises: f4a7c2e1b9d3
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f4a7c2e1b9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

auth_provider_enum = sa.Enum('local', 'google', name='auth_provider')


def upgrade() -> None:
    auth_provider_enum.create(op.get_bind(), checkfirst=True)

    # Existing accounts are unaffected: password_hash stays populated for
    # all of them, auth_provider defaults server-side to 'local' on the
    # add_column itself (so the backfill is part of the DDL, not a
    # separate UPDATE), and google_sub stays NULL for everyone until they
    # actually link a Google account.
    op.alter_column('users', 'password_hash', existing_type=sa.String(), nullable=True)
    op.add_column(
        'users',
        sa.Column('auth_provider', auth_provider_enum, nullable=False, server_default='local'),
    )
    op.add_column('users', sa.Column('google_sub', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_google_sub', 'users', ['google_sub'])
    op.create_index('ix_users_google_sub', 'users', ['google_sub'])


def downgrade() -> None:
    op.drop_index('ix_users_google_sub', table_name='users')
    op.drop_constraint('uq_users_google_sub', 'users', type_='unique')
    op.drop_column('users', 'google_sub')
    op.drop_column('users', 'auth_provider')
    op.alter_column('users', 'password_hash', existing_type=sa.String(), nullable=False)
    auth_provider_enum.drop(op.get_bind(), checkfirst=True)
