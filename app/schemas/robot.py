"""Robot status schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RobotStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amr_code: str = Field(alias="amrCode")
    x: Optional[float] = None
    y: Optional[float] = None
    state: Optional[str] = None
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
