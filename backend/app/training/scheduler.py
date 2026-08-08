"""
Training Scheduler — APScheduler Weekly Job
=============================================
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.training.trainer import get_training_pipeline

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _training_job():
    """Scheduled job that triggers the weekly training pipeline."""
    logger.info("=" * 50)
    logger.info("SCHEDULED TRAINING JOB STARTED")
    logger.info("=" * 50)

    pipeline = get_training_pipeline()
    result = await pipeline.run_training()

    if result:
        logger.info("Training complete. New model version: %d", result)
    else:
        logger.info("Training skipped or failed. No new model version.")


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with the weekly training job."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    # Parse cron expression: "0 2 * * 0" → minute=0, hour=2, day_of_week=sun
    parts = settings.training_schedule_cron.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )

    _scheduler.add_job(
        _training_job,
        trigger=trigger,
        id="weekly_training",
        name="Weekly Model Training",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Training scheduler started. Cron: %s",
        settings.training_schedule_cron,
    )
    return _scheduler


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Training scheduler stopped.")
