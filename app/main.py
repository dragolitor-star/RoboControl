"""FastAPI application factory + lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.api.v1.routers.health import router as health_router
from app.clients.rcs2000_client import init_rcs_client, shutdown_rcs_client
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.init_seed import seed_robot_types
from app.db.session import AsyncSessionLocal, engine
from app.middleware.request_context import RequestContextMiddleware
from app.utils.redis_helper import close_redis, get_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("startup_begin", env=settings.APP_ENV, app=settings.APP_NAME)

    # Database connectivity sanity check.
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("startup_db_failed", error=str(exc))
        raise

    # Redis ping.
    redis_client = await get_redis()
    try:
        await redis_client.ping()
    except Exception as exc:
        logger.error("startup_redis_failed", error=str(exc))
        raise

    # Long-lived RCS HTTP client.
    init_rcs_client()

    # Idempotent seed of RobotType reference data.
    try:
        await seed_robot_types()
    except Exception as exc:  # pragma: no cover - guard rather than crash boot
        logger.warning("seed_failed", error=str(exc))

    logger.info("startup_done")
    try:
        yield
    finally:
        logger.info("shutdown_begin")
        await shutdown_rcs_client()
        await close_redis()
        await engine.dispose()
        logger.info("shutdown_done")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RCS-2000 Middleware",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.APP_ENV != "prod" or settings.DEBUG else None,
        docs_url="/docs" if settings.APP_ENV != "prod" or settings.DEBUG else None,
        redoc_url="/redoc" if settings.APP_ENV != "prod" or settings.DEBUG else None,
    )

    _setup_cors(app)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(health_router)

    register_exception_handlers(app)
    _setup_telemetry(app)

    # Serve web dashboard UI — must be last so API routes take precedence.
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


def _setup_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _setup_telemetry(app: FastAPI) -> None:
    """Optional OpenTelemetry instrumentation.

    TODO(OTel): wire OTLP exporter once collector endpoint is decided. The
    lazy import keeps OTel optional so dev installs don't need it.
    """
    if not settings.OTEL_ENABLED:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel_enabled")
    except Exception as exc:  # pragma: no cover
        logger.warning("otel_init_failed", error=str(exc))


app = create_app()
