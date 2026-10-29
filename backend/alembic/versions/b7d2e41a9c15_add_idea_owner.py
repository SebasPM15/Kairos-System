"""add ideas.user_id

Revision ID: b7d2e41a9c15
Revises: a3f1c9d27b40
Create Date: 2026-10-29 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.config import get_settings


# revision identifiers, used by Alembic.
revision: str = 'b7d2e41a9c15'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d27b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _default_user_id(bind) -> int:
    """The configured single user if present, else the oldest user, else a new one."""
    telegram_id = get_settings().telegram_allowed_user_id
    row = bind.execute(
        sa.text("SELECT id FROM users WHERE telegram_id IS :tid"), {"tid": telegram_id}
    ).first() or bind.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).first()
    if row is not None:
        return row[0]
    bind.execute(
        sa.text("INSERT INTO users (telegram_id, created_at) VALUES (:tid, CURRENT_TIMESTAMP)"),
        {"tid": telegram_id},
    )
    return bind.execute(sa.text("SELECT id FROM users ORDER BY id DESC LIMIT 1")).scalar_one()


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ideas') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    bind = op.get_bind()
    # Ideas in a project belong to the project's owner; inbox ideas to the default user
    bind.execute(sa.text(
        "UPDATE ideas SET user_id = (SELECT user_id FROM projects WHERE projects.id = ideas.project_id) "
        "WHERE project_id IS NOT NULL"
    ))
    if bind.execute(sa.text("SELECT COUNT(*) FROM ideas WHERE user_id IS NULL")).scalar_one() > 0:
        bind.execute(
            sa.text("UPDATE ideas SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": _default_user_id(bind)},
        )

    with op.batch_alter_table('ideas') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_ideas_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ideas') as batch_op:
        batch_op.drop_constraint('fk_ideas_user_id_users', type_='foreignkey')
        batch_op.drop_column('user_id')
