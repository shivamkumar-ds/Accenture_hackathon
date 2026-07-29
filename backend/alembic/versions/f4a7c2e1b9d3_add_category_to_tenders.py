"""add category to tenders

Revision ID: f4a7c2e1b9d3
Revises: b3f8e21d5a91
Create Date: 2026-07-30 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a7c2e1b9d3'
down_revision: Union[str, None] = 'b3f8e21d5a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenders', sa.Column('category', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tenders', 'category')
