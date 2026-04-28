"""Add reviewer system: role to telegram_accounts, approved_l1 status, review fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create TgRole enum and add role column to telegram_accounts
    tg_role_enum = sa.Enum('employee', 'reviewer_l1', 'reviewer_l2', name='tg_role_enum')
    tg_role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('telegram_accounts', sa.Column(
        'role', tg_role_enum, nullable=False, server_default='employee',
    ))

    # 2. Add approved_l1 to request_status_enum
    # PostgreSQL: add value to existing enum
    op.execute("ALTER TYPE request_status_enum ADD VALUE IF NOT EXISTS 'approved_l1' AFTER 'in_progress'")

    # 3. Add review fields to requests
    op.add_column('requests', sa.Column('photo_file_id', sa.String(512), nullable=True))
    op.add_column('requests', sa.Column('l1_reviewer_tg_id', sa.BigInteger(), nullable=True))
    op.add_column('requests', sa.Column('l1_comment', sa.Text(), nullable=True))
    op.add_column('requests', sa.Column('l2_reviewer_tg_id', sa.BigInteger(), nullable=True))

    # 4. Assign tg ID 747912852 as reviewer_l1
    op.execute(
        "UPDATE telegram_accounts SET role = 'reviewer_l1' "
        "WHERE telegram_user_id = 747912852"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE telegram_accounts SET role = 'employee' "
        "WHERE telegram_user_id = 747912852"
    )
    op.drop_column('requests', 'l2_reviewer_tg_id')
    op.drop_column('requests', 'l1_comment')
    op.drop_column('requests', 'l1_reviewer_tg_id')
    op.drop_column('requests', 'photo_file_id')
    op.drop_column('telegram_accounts', 'role')
    sa.Enum(name='tg_role_enum').drop(op.get_bind(), checkfirst=True)
    # Note: cannot remove value from PostgreSQL enum, approved_l1 stays
