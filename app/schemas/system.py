"""System API schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

class ConnectionSettingsUpdate(BaseModel):
    rcs_ip: str = Field(..., description="IP address of the RCS server")
    rcs_port: int = Field(..., description="Port of the RCS server")

class ConnectionSettingsResponse(BaseModel):
    rcs_ip: str | None = Field(None, description="IP address of the RCS server")
    rcs_port: int | None = Field(None, description="Port of the RCS server")
    rcs_base_url: str = Field(..., description="Currently resolved Base URL")
