"""Webhook payloads from RCS-2000."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskFeedbackPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    robot_task_code: str = Field(alias="robotTaskCode", min_length=1)
    method: str = Field(min_length=1, description="start | outbin | end | ...")
    x: Optional[float] = None
    y: Optional[float] = None
    amr_code: Optional[str] = Field(default=None, alias="amrCode")
    error_msg: Optional[str] = Field(default=None, alias="errorMsg")


class WebhookAck(BaseModel):
    acknowledged: bool = True
    duplicate: bool = False
