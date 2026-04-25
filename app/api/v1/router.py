"""Aggregate router for /api/v1."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import alerts, robots, system, tasks, webhook_logs, webhooks

api_v1_router = APIRouter()
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(robots.router)
api_v1_router.include_router(webhooks.router)
api_v1_router.include_router(webhook_logs.router)
api_v1_router.include_router(system.router)
api_v1_router.include_router(alerts.router)

