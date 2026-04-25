"""Shared response envelopes."""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class StandardResponse(BaseModel, Generic[T]):
    """Uniform response envelope used by every endpoint, success or failure."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool
    request_id: str = Field(alias="requestId", default="")
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
