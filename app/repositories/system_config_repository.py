"""Repository for system configuration."""
from __future__ import annotations

from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system_config import SystemConfig


class SystemConfigRepository:
    """Repository for managing system configurations with Redis caching."""

    def __init__(self, session: AsyncSession, redis_client: Redis) -> None:
        self.session = session
        self.redis = redis_client

    async def get(self, key: str) -> str | None:
        """Get a configuration value, preferring Redis cache."""
        redis_key = f"sysconfig:{key}"
        cached = await self.redis.get(redis_key)
        if cached is not None:
            return cached

        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await self.session.execute(stmt)
        config_obj = result.scalar_one_or_none()

        if config_obj and config_obj.value is not None:
            await self.redis.set(redis_key, config_obj.value)
            return config_obj.value

        return None

    async def set(self, key: str, value: str) -> None:
        """Set a configuration value in DB and cache."""
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await self.session.execute(stmt)
        config_obj = result.scalar_one_or_none()

        if config_obj:
            config_obj.value = value
        else:
            config_obj = SystemConfig(key=key, value=value)
            self.session.add(config_obj)

        await self.session.commit()
        await self.redis.set(f"sysconfig:{key}", value)

    async def get_connection_settings(self) -> dict[str, Any]:
        """Get RCS connection settings."""
        ip = await self.get("rcs_ip")
        port = await self.get("rcs_port")
        
        if ip and port:
            base_url = f"http://{ip}:{port}"
        else:
            base_url = settings.RCS_BASE_URL
            
        return {
            "rcs_ip": ip,
            "rcs_port": int(port) if port else None,
            "rcs_base_url": base_url
        }
