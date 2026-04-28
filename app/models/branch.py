import enum
import sqlalchemy as sa
from app.database import Base


class LocationType(str, enum.Enum):
    city = "city"
    regional = "regional"


class BhmBranch(Base):
    """Филиалы банка (BXM)."""

    __tablename__ = "bhm_branches"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    bhm_code: str = sa.Column(sa.String(5), unique=True, nullable=False, index=True)
    branch_name: str = sa.Column(sa.String(255), nullable=False)
    region_name: str = sa.Column(sa.String(255), nullable=False)
    city_name: str = sa.Column(sa.String(255), nullable=False)
    location_type: str = sa.Column(
        sa.Enum(LocationType, name="location_type_enum", create_constraint=True),
        nullable=False,
        default=LocationType.regional,
    )
    is_active: bool = sa.Column(sa.Boolean, default=True, nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<BhmBranch {self.bhm_code} – {self.branch_name}>"
