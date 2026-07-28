import logging
from uuid import uuid4

import pytest

from app.services.outbox_service import (
    ConsoleTransport,
    OutboxEnvelope,
    OutboxService,
    delivery_error_summary,
)


@pytest.mark.asyncio
async def test_console_transport_logs_only_bounded_delivery_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    envelope = OutboxEnvelope(
        id=uuid4(),
        deduplication_key="incident:abc:sla:response:breach",
        topic="sla.breached",
        recipient="private@example.com",
        payload={
            "incident_id": "abc",
            "objective": "response",
            "title": "Sensitive production incident",
            "secret": "do-not-log",
        },
        attempt=2,
    )
    with caplog.at_level(logging.INFO):
        await ConsoleTransport().send(envelope)

    record = caplog.records[-1]
    assert record.message == "outbox delivery"
    assert record.incident_id == "abc"
    assert record.objective == "response"
    assert record.attempt == 2
    assert not hasattr(record, "recipient")
    assert not hasattr(record, "payload")
    assert "Sensitive production incident" not in caplog.text
    assert "private@example.com" not in caplog.text


class _LeakingTransport:
    async def send(self, envelope: OutboxEnvelope) -> None:
        raise RuntimeError(f"provider rejected {envelope.recipient}")


class _DeliveryHarness(OutboxService):
    async def claim_batch(self, *, now=None):
        return [
            OutboxEnvelope(
                id=uuid4(),
                deduplication_key="incident:abc:sla:response:breach",
                topic="sla.breached",
                recipient="private@example.com",
                payload={"incident_id": "abc", "title": "Sensitive incident"},
                attempt=1,
            )
        ]

    async def mark_failed(self, envelope, *, error, now=None):
        return None

    async def mark_sent(self, envelope, *, now=None):
        raise AssertionError("failed delivery must not be marked sent")


@pytest.mark.asyncio
async def test_delivery_failure_log_does_not_include_transport_exception_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    harness = _DeliveryHarness(object(), settings=object())
    with caplog.at_level(logging.ERROR):
        result = await harness.deliver_once(transport=_LeakingTransport())

    assert result == {"claimed": 1, "sent": 0, "failed": 1}
    assert "private@example.com" not in caplog.text
    assert "Sensitive incident" not in caplog.text
    assert caplog.records[-1].error_type == "RuntimeError"


def test_delivery_error_summary_omits_provider_text() -> None:
    assert (
        delivery_error_summary(RuntimeError("recipient@example.com token=private"))
        == "RuntimeError"
    )
