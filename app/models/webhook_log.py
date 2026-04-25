"""WebhookLog ORM model — persists every incoming webhook event for auditing."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_task_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amr_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    x: Mapped[float | None] = mapped_column(nullable=True)
    y: Mapped[float | None] = mapped_column(nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
