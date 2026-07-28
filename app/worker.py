"""Database-backed SLA evaluator and outbox delivery worker."""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.config import get_settings
from app.database import dispose_database, get_session_factory
from app.logging import configure_logging
from app.services.outbox_service import OutboxService, build_transport
from app.services.sla_service import SLAEvaluationService

logger = logging.getLogger(__name__)


async def evaluate_once() -> dict[str, int]:
    settings = get_settings()
    async with get_session_factory()() as session:
        summary = await SLAEvaluationService(session).evaluate_once(
            batch_size=settings.worker_batch_size
        )
    return {
        "incidents_examined": summary.incidents_examined,
        "objectives_breached": summary.objectives_breached,
    }


async def deliver_once() -> dict[str, int]:
    settings = get_settings()
    transport = build_transport(settings)
    async with get_session_factory()() as session:
        return await OutboxService(session, settings=settings).deliver_once(transport=transport)


async def run_cycle() -> dict[str, dict[str, int] | None]:
    evaluation: dict[str, int] | None = None
    delivery: dict[str, int] | None = None
    try:
        evaluation = await evaluate_once()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("SLA evaluation cycle failed")

    try:
        delivery = await deliver_once()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("outbox delivery cycle failed")

    result = {"evaluation": evaluation, "delivery": delivery}
    logger.info("worker cycle", extra=result)
    return result


async def run_forever() -> None:
    settings = get_settings()
    while True:
        await run_cycle()
        await asyncio.sleep(settings.worker_poll_seconds)


async def _main_async(command: str) -> None:
    try:
        if command == "evaluate-once":
            print(await evaluate_once())
        elif command == "deliver-once":
            print(await deliver_once())
        else:
            await run_forever()
    finally:
        await dispose_database()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("run", "evaluate-once", "deliver-once"),
        nargs="?",
        default="run",
    )
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(_main_async(args.command))


if __name__ == "__main__":
    main()
