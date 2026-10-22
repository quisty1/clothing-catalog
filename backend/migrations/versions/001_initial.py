"""Products and durable Telegram deduplication."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None


def upgrade():
    op.create_table('products',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('object_key', sa.String(200), nullable=False, unique=True),
        sa.Column('source_key', sa.String(200), nullable=False, unique=True),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('processed_updates',
        sa.Column('bot_id', sa.BigInteger(), primary_key=True),
        sa.Column('update_id', sa.BigInteger(), primary_key=True),
        sa.Column('response', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade():
    op.drop_table('processed_updates')
    op.drop_table('products')
