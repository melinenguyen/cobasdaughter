"""
APScheduler-based daily 10AM scheduler.

Run this process on any server (local machine, VPS, Docker) and it will
automatically fire the trend agent every day at 10:00 AM in the configured
timezone, then serve the Flask dashboard on the configured port.
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from agent.config import Config
from agent.main import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")

DASHBOARD_URL = os.getenv("DASHBOARD_URL", f"http://localhost:{Config.DASHBOARD_PORT}")


def scheduled_run():
    logger.info("Scheduled trend run triggered")
    try:
        result = run_agent(dashboard_url=DASHBOARD_URL)
        logger.info(f"Scheduled run complete: {result}")
    except Exception as e:
        logger.error(f"Scheduled run failed: {e}")


def start():
    tz = pytz.timezone(Config.SCHEDULER_TIMEZONE)
    scheduler = BackgroundScheduler(timezone=tz)

    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(hour=10, minute=0, timezone=tz),
        id="daily_trend_report",
        name="Daily US Trend Report at 10AM",
        replace_existing=True,
        misfire_grace_time=1800,  # 30 min grace period
    )

    scheduler.start()
    logger.info(
        f"Scheduler started — daily trend report at 10:00 AM {Config.SCHEDULER_TIMEZONE}"
    )

    # Start Flask dashboard
    from dashboard.app import app
    port = Config.DASHBOARD_PORT
    logger.info(f"Dashboard available at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start()
