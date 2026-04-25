"""TaskHistory ORM model + status enum."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskHistory(Base, TimestampMixin):
    __tablename__ = "task_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_task_code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum"), nullable=False, index=True
    )
    robot_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    source_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TaskHistory(id={self.id}, robot_task_code={self.robot_task_code!r}, "
            f"status={self.status})"
        )
