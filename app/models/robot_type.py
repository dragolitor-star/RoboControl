"""RobotType ORM model."""
from __future__ import annotations

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RobotType(Base, TimestampMixin):
    __tablename__ = "robot_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rcs_task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    __table_args__ = (Index("ix_robot_types_name_rcs", "name", "rcs_task_type"),)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"RobotType(id={self.id}, name={self.name!r}, rcs_task_type={self.rcs_task_type!r})"
