"""Persist upload intent across stateless bot instances."""
from alembic import op
import sqlalchemy as sa

revision='002'
down_revision='001'


def upgrade():
    op.create_table('admin_prompts',
        sa.Column('bot_id',sa.BigInteger(),primary_key=True),
        sa.Column('user_id',sa.BigInteger(),primary_key=True),
        sa.Column('awaiting_photo',sa.Boolean(),nullable=False))


def downgrade():
    op.drop_table('admin_prompts')
