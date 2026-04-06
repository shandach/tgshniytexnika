import sqlalchemy as sa
from app.database import Base


class Employee(Base):
    """Сотрудники банка (создаются при первой заявке)."""

    __tablename__ = "employees"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    fio_original: str = sa.Column(sa.String(512), nullable=False)
    fio_normalized: str = sa.Column(sa.String(512), nullable=False, index=True)
    position: str = sa.Column(sa.Text, nullable=True)
    branch_id: int = sa.Column(
        sa.Integer, sa.ForeignKey("bhm_branches.id"), nullable=False
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    branch = sa.orm.relationship("BhmBranch", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Employee {self.fio_original}>"
