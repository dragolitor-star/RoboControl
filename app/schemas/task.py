"""Task-related request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    robot_type: str = Field(alias="robotType", min_length=1, max_length=50)
    source_code: str = Field(alias="sourceCode", min_length=1, max_length=100)
    target_code: str = Field(alias="targetCode", min_length=1, max_length=100)
    priority: int = Field(default=10, ge=1, le=100)


class TaskCreateResponseData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    robot_task_code: str = Field(alias="robotTaskCode")
    status: str
    cached: bool = Field(default=False, description="True if served from idempotency cache.")


class TaskHistoryItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    robot_task_code: str = Field(alias="robotTaskCode")
    status: str
    robot_code: Optional[str] = Field(default=None, alias="robotCode")
    source_code: Optional[str] = Field(default=None, alias="sourceCode")
    target_code: Optional[str] = Field(default=None, alias="targetCode")
    error_msg: Optional[str] = Field(default=None, alias="errorMsg")
