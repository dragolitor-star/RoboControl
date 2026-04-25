"""Idempotent startup seed for `robot_types`.

Runs on application start. Safe to call repeatedly; existing rows are skipped.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.robot_type import RobotType

logger = get_logger(__name__)

DEFAULT_ROBOT_TYPES: list[dict[str, str]] = [
    {"name": "LMR", "rcs_task_type": "PF-LMR-COMMON", "description": "Light Mobile Robot"},
    {"name": "FMR", "rcs_task_type": "PF-FMR-COMMON", "description": "Forklift Mobile Robot"},
    {"name": "CT7", "rcs_task_type": "PF-CTU-COMMON", "description": "Container 7-tier"},
]


async def seed_robot_types(session: AsyncSession | None = None) -> None:
    own_session = session is None
    session = session or AsyncSessionLocal()
    try:
        existing = (await session.execute(select(RobotType.name))).scalars().all()
        existing_names = set(existing)
        added = 0
        for spec in DEFAULT_ROBOT_TYPES:
            if spec["name"] in existing_names:
                continue
            session.add(RobotType(**spec))
            added += 1
        if added:
            await session.commit()
        logger.info("seed_robot_types_done", added=added, total=len(DEFAULT_ROBOT_TYPES))
    finally:
        if own_session:
            await session.close()
