"""add ideas.assigned_at

Revision ID: c4e8a1d36f72
Revises: b7d2e41a9c15
Create Date: 2026-11-03 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1d36f72'
down_revision: Union[str, Sequence[str], None] = 'b7d2e41a9c15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ideas') as batch_op:
        batch_op.add_column(sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))

    # The real assignment date was never recorded; the capture date is the best estimate
    op.execute("UPDATE ideas SET assigned_at = created_at WHERE project_id IS NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ideas') as batch_op:
        batch_op.drop_column('assigned_at')
