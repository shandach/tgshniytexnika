import enum
import sqlalchemy as sa
from app.database import Base


class EquipmentType(str, enum.Enum):
    computer = "computer"
    printer = "printer"


class InventoryStatus(str, enum.Enum):
    active = "active"
    repair = "repair"
    replaced = "replaced"


class Inventory(Base):
    """
    Инвентарь техники (компьютеры и принтеры).

    Статус может меняться автоматически при одобрении
    заявки на поломку (active → repair) и вручную
    проверяющим (repair → active, active → replaced и т.д.).
    """

    __tablename__ = "inventory"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    inventory_code: str = sa.Column(sa.String(64), unique=True, nullable=False, index=True)
    branch_id: int = sa.Column(
        sa.Integer, sa.ForeignKey("bhm_branches.id"), nullable=False
    )
    equipment_type: str = sa.Column(
        sa.Enum(EquipmentType, name="equipment_type_enum", create_constraint=True),
        nullable=False,
    )
    issue_year: int = sa.Column(sa.Integer, nullable=False)
    status: str = sa.Column(
        sa.Enum(InventoryStatus, name="inventory_status_enum", create_constraint=True),
        nullable=False,
        default=InventoryStatus.active,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    branch = sa.orm.relationship("BhmBranch", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Inventory {self.inventory_code} ({self.equipment_type})>"
