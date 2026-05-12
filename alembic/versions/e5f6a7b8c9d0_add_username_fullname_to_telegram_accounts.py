"""add username and full_name to telegram_accounts

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('telegram_accounts', sa.Column('username', sa.String(255), nullable=True))
    op.add_column('telegram_accounts', sa.Column('full_name', sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column('telegram_accounts', 'full_name')
    op.drop_column('telegram_accounts', 'username')
