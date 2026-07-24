"""baseline (empty, no models yet)

Revision ID: 265e4dc23a06
Revises: 
Create Date: 2026-07-15 15:30:01.240166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '265e4dc23a06'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
