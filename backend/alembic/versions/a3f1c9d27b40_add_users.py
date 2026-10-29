"""add users and scope projects by user

Revision ID: a3f1c9d27b40
Revises: cb1197fef8ca
Create Date: 2026-10-28 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.config import get_settings


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d27b40'
down_revision: Union[str, Sequence[str], None] = 'cb1197fef8ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The initial migration left the slug UNIQUE unnamed; this names it so batch mode can drop it
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    """Upgrade schema."""
    users = op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('telegram_id')
    )

    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    # Existing projects belong to the default user (the allowed Telegram user, if configured).
    # With no projects there is nothing to adopt; get_current_user creates the user lazily.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM projects")).scalar_one() > 0:
        bind.execute(
            sa.insert(users).values(
                telegram_id=get_settings().telegram_allowed_user_id,
                # Raw insert bypasses UTCDateTime; SQLite CURRENT_TIMESTAMP is already UTC
                created_at=sa.func.current_timestamp(),
            )
        )
        default_id = bind.execute(sa.text("SELECT id FROM users")).scalar_one()
        bind.execute(sa.text("UPDATE projects SET user_id = :uid"), {"uid": default_id})

    with op.batch_alter_table('projects', naming_convention=NAMING) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_projects_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('uq_projects_slug', type_='unique')
        batch_op.create_unique_constraint('uq_projects_user_id_slug', ['user_id', 'slug'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('projects', naming_convention=NAMING) as batch_op:
        batch_op.drop_constraint('uq_projects_user_id_slug', type_='unique')
        batch_op.drop_constraint('fk_projects_user_id_users', type_='foreignkey')
        batch_op.create_unique_constraint('uq_projects_slug', ['slug'])
        batch_op.drop_column('user_id')
    op.drop_table('users')
