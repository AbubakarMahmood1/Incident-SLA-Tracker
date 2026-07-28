from unittest.mock import AsyncMock

import pytest

import app.worker as worker


@pytest.mark.asyncio
async def test_delivery_still_runs_when_evaluation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = AsyncMock(side_effect=RuntimeError("evaluation failed"))
    delivery = AsyncMock(return_value={"claimed": 1, "sent": 1, "failed": 0})
    monkeypatch.setattr(worker, "evaluate_once", evaluation)
    monkeypatch.setattr(worker, "deliver_once", delivery)

    result = await worker.run_cycle()

    assert result == {
        "evaluation": None,
        "delivery": {"claimed": 1, "sent": 1, "failed": 0},
    }
    delivery.assert_awaited_once()


@pytest.mark.asyncio
async def test_evaluation_still_survives_delivery_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = AsyncMock(return_value={"incidents_examined": 1, "objectives_breached": 1})
    delivery = AsyncMock(side_effect=RuntimeError("delivery failed"))
    monkeypatch.setattr(worker, "evaluate_once", evaluation)
    monkeypatch.setattr(worker, "deliver_once", delivery)

    result = await worker.run_cycle()

    assert result == {
        "evaluation": {"incidents_examined": 1, "objectives_breached": 1},
        "delivery": None,
    }
