"""add assigned_region to telegram_accounts

Revision ID: d4e5f6a7b8c9
Revises: 9f251be2379c
Create Date: 2026-04-28 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '9f251be2379c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'telegram_accounts',
        sa.Column('assigned_region', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('telegram_accounts', 'assigned_region')
