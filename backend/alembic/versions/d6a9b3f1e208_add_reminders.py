"""add reminder_log and project_reminder_prefs

Revision ID: d6a9b3f1e208
Revises: c4e8a1d36f72
Create Date: 2026-11-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a9b3f1e208'
down_revision: Union[str, Sequence[str], None] = 'c4e8a1d36f72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Only new tables: nothing existing is rebuilt and nothing needs a backfill."""
    op.create_table('reminder_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('stalled', 'ready_to_finish', name='reminderkind', native_enum=False), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('local_date', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'project_id', 'kind', 'local_date', name='uq_reminder_log_per_day')
    )
    op.create_index('ix_reminder_log_user_id_sent_at', 'reminder_log', ['user_id', 'sent_at'], unique=False)
    op.create_table('project_reminder_prefs',
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('snoozed_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('muted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('project_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('project_reminder_prefs')
    op.drop_index('ix_reminder_log_user_id_sent_at', table_name='reminder_log')
    op.drop_table('reminder_log')
