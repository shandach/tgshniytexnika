"""add fsm_state table for persistent bot state storage"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = '3cd42698dc3c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS fsm_state (
            bot_id      BIGINT       NOT NULL,
            chat_id     BIGINT       NOT NULL,
            user_id     BIGINT       NOT NULL,
            destiny     VARCHAR(255) NOT NULL DEFAULT 'default',
            state       VARCHAR(255),
            data        JSONB,
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (bot_id, chat_id, user_id, destiny)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_fsm_state_user_id ON fsm_state (user_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fsm_state")
