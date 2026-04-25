"""Webhook log schemas for the dashboard viewer."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WebhookLogItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    robot_task_code: str = Field(alias="robotTaskCode")
    method: str
    amr_code: Optional[str] = Field(default=None, alias="amrCode")
    x: Optional[float] = None
    y: Optional[float] = None
    signature_valid: bool = Field(alias="signatureValid")
    duplicate: bool
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
