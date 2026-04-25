"""Dashboard statistics schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SystemStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    active_robots: int = Field(alias="activeRobots", default=0)
    pending_tasks: int = Field(alias="pendingTasks", default=0)
    running_tasks: int = Field(alias="runningTasks", default=0)
    completed_tasks_today: int = Field(alias="completedTasksToday", default=0)
    failed_tasks_today: int = Field(alias="failedTasksToday", default=0)
    total_tasks: int = Field(alias="totalTasks", default=0)
    db_status: str = Field(alias="dbStatus", default="unknown")
    redis_status: str = Field(alias="redisStatus", default="unknown")
