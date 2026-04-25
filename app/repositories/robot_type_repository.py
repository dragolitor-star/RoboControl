"""Repository for `RobotType` queries."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.robot_type import RobotType


class RobotTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> RobotType | None:
        stmt = select(RobotType).where(RobotType.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[RobotType]:
        stmt = select(RobotType).order_by(RobotType.name)
        return list((await self._session.execute(stmt)).scalars().all())
