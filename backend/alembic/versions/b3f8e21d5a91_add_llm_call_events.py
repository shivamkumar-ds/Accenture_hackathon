"""add llm_call_events (Phase A instrumentation)

Revision ID: b3f8e21d5a91
Revises: 9c1f4b7a2e3d
Create Date: 2026-07-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3f8e21d5a91'
down_revision: Union[str, None] = '9c1f4b7a2e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_call_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False, server_default='unspecified'),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_type', sa.String(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('evaluation_path', sa.String(), nullable=False, server_default='llm'),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=True),
        sa.Column('mission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('missions.id'), nullable=True),
    )
    # Index the columns Phase B's baseline queries will actually filter/group
    # by (per-purpose token/latency breakdowns, recent-window queries) --
    # no dashboard yet, but the queries behind one shouldn't require a table
    # scan on day one.
    op.create_index('ix_llm_call_events_purpose', 'llm_call_events', ['purpose'])
    op.create_index('ix_llm_call_events_created_at', 'llm_call_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_llm_call_events_created_at', table_name='llm_call_events')
    op.drop_index('ix_llm_call_events_purpose', table_name='llm_call_events')
    op.drop_table('llm_call_events')
