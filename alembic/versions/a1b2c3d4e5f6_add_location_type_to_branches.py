"""Add location_type to bhm_branches

Revision ID: a1b2c3d4e5f6
Revises: 21b9e95f491b
Create Date: 2026-04-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '21b9e95f491b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    location_type_enum = sa.Enum('city', 'regional', name='location_type_enum', create_constraint=True)
    location_type_enum.create(op.get_bind(), checkfirst=True)

    # Add column with default value
    op.add_column('bhm_branches', sa.Column(
        'location_type',
        location_type_enum,
        nullable=False,
        server_default='regional',
    ))


def downgrade() -> None:
    op.drop_column('bhm_branches', 'location_type')
    sa.Enum(name='location_type_enum').drop(op.get_bind(), checkfirst=True)
