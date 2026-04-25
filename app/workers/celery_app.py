"""Celery factory.

Run a worker with:
    celery -A app.workers.celery_app worker -l info
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings


def create_celery_app() -> Celery:
    app = Celery(
        "rcs_middleware",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.workers.tasks"],
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_queue="rcs.default",
        worker_prefetch_multiplier=4,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = create_celery_app()
