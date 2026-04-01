"""
APScheduler-based background scheduler for daily capture pipeline.

Configured via CAPTURE_SCHEDULE_HOUR setting (default: 2 = 2:00 AM UTC).
"""

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.workers.tasks import run_daily_capture_all

logger = structlog.get_logger()

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Start the background scheduler with the daily capture job."""
    hour = getattr(settings, "CAPTURE_SCHEDULE_HOUR", 2)

    scheduler.add_job(
        _run_daily_wrapper,
        CronTrigger(hour=hour, minute=0),
        id="daily_capture",
        name="Daily AI capture pipeline",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("scheduler_started", capture_hour=hour)


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")


async def _run_daily_wrapper() -> None:
    """Wrapper to run the daily capture with error handling."""
    try:
        await run_daily_capture_all()
    except Exception as exc:
        logger.error("scheduler_daily_capture_failed", error=str(exc))
