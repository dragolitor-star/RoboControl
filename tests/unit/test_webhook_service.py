"""Unit tests for the webhook → Celery flow.

We bypass Celery itself by patching `process_task_feedback.delay` so the
tests focus on signature verification + dedupe + dispatch decision.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from app.core.exceptions import WebhookSignatureError
from app.schemas.webhook import TaskFeedbackPayload
from app.services.webhook_service import WebhookService
from app.workers import tasks as worker_tasks


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_method_end_sets_completed(redis_mock, monkeypatch):
    captured: list[dict] = []
    monkeypatch.setattr(
        worker_tasks.process_task_feedback,
        "delay",
        lambda payload: captured.append(payload) or "task-id",
    )

    body_dict = {
        "robotTaskCode": "T-1",
        "method": "end",
        "amrCode": "AMR-1",
        "x": 1.0,
        "y": 2.0,
    }
    raw = json.dumps(body_dict).encode()
    sig = _sign(raw, "test-webhook-secret")

    svc = WebhookService(redis_client=redis_mock)
    payload = TaskFeedbackPayload.model_validate(body_dict)
    ack = await svc.handle_task_feedback(raw_body=raw, signature=sig, payload=payload)
    assert ack.acknowledged is True
    assert ack.duplicate is False
    assert captured and captured[0]["method"] == "end"


@pytest.mark.asyncio
async def test_invalid_signature_raises(redis_mock):
    body = b'{"robotTaskCode":"X","method":"start"}'
    payload = TaskFeedbackPayload.model_validate({"robotTaskCode": "X", "method": "start"})
    svc = WebhookService(redis_client=redis_mock)
    with pytest.raises(WebhookSignatureError):
        await svc.handle_task_feedback(raw_body=body, signature="deadbeef", payload=payload)


@pytest.mark.asyncio
async def test_duplicate_event_is_idempotent(redis_mock, monkeypatch):
    counter = {"n": 0}
    monkeypatch.setattr(
        worker_tasks.process_task_feedback,
        "delay",
        lambda payload: counter.update(n=counter["n"] + 1),
    )

    body_dict = {"robotTaskCode": "T-2", "method": "start", "amrCode": "AMR-1"}
    raw = json.dumps(body_dict).encode()
    sig = _sign(raw, "test-webhook-secret")
    payload = TaskFeedbackPayload.model_validate(body_dict)

    svc = WebhookService(redis_client=redis_mock)
    first = await svc.handle_task_feedback(raw_body=raw, signature=sig, payload=payload)
    second = await svc.handle_task_feedback(raw_body=raw, signature=sig, payload=payload)
    assert first.duplicate is False
    assert second.duplicate is True
    assert counter["n"] == 1


@pytest.mark.asyncio
async def test_method_mapping(redis_mock, monkeypatch):
    """Validate the static method→status table without booting Celery."""
    from app.core.constants import TASK_METHOD_TO_STATUS

    assert TASK_METHOD_TO_STATUS["start"] == "running"
    assert TASK_METHOD_TO_STATUS["outbin"] == "running"
    assert TASK_METHOD_TO_STATUS["end"] == "completed"
    assert TASK_METHOD_TO_STATUS.get("unknown") is None
