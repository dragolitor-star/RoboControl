"""Task-related request/response schemas."""
from __future__ import annotations

from typing import Any, Literal, Optional

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


class RcsSubmitPreviewData(BaseModel):
    """UI: resolved host + default task-submit path and sample JSON."""

    model_config = ConfigDict(populate_by_name=True)

    resolved_base_url: str = Field(alias="resolvedBaseUrl")
    method: Literal["POST", "GET"] = "POST"
    path: str
    full_url_without_sign: str = Field(alias="fullUrlWithoutSign")
    example_body: dict[str, Any] = Field(alias="exampleBody")


class RcsRawSubmitRequest(BaseModel):
    """Raw request to RCS; supports signed or Postman-compatible mode."""

    model_config = ConfigDict(populate_by_name=True)

    method: Literal["POST", "GET"] = "POST"
    path: str = Field(..., min_length=1, description="Path or full URL; host is ignored.")
    body: dict[str, Any] | None = None
    send_signed: bool = Field(
        default=False,
        alias="sendSigned",
        description="Use middleware signature strategy; false mimics Postman-style plain call.",
    )
    persist_task: bool = Field(
        default=True,
        alias="persistTask",
        description="If true, store TaskHistory when robotTaskCode is returned.",
    )


class RcsRawSubmitResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    robot_task_code: Optional[str] = Field(default=None, alias="robotTaskCode")
    status: Optional[str] = None
    cached: bool = Field(default=False, alias="cached")
    persisted: bool = Field(default=False, alias="persisted")
    rcs: dict[str, Any] = Field(
        alias="rcsResponse",
        description="Raw JSON from RCS after successful HTTP call.",
    )
