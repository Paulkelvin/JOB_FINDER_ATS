from __future__ import annotations

import logging
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .search.pipeline import run_gis_scan
from .discord_integration.webhook import send_job_card, send_summary


logger = logging.getLogger("geo_job_sentinel.scheduler")


def _scan_job() -> None:
    logger.info("Starting scheduled GIS scan at %s", datetime.utcnow().isoformat())
    jobs, stats = run_gis_scan()
    for job in jobs:
        send_job_card(job)
    send_summary(jobs, stats)
    logger.info("Completed scheduled scan: %s", stats)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = BlockingScheduler(timezone="UTC")

    # Daily summary hour (UTC)
    hour_utc = int(os.getenv("DAILY_SUMMARY_HOUR_UTC", "18"))

    scheduler.add_job(
        _scan_job,
        CronTrigger(hour=hour_utc, minute=0),
        id="daily_gis_scan",
        replace_existing=True,
    )

    logger.info("Scheduler started. Daily GIS scan at %02d:00 UTC", hour_utc)
    scheduler.start()


if __name__ == "__main__":  # pragma: no cover
    main()
