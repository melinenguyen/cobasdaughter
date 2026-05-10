"""
APScheduler-based scheduler: runs the trend agent at 9AM and 3PM ET daily.

Run this process on any server (local machine, VPS, Docker) and it will
fire automatically twice a day, then serve the Flask dashboard.
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
        trigger=CronTrigger(hour=9, minute=0, timezone=tz),
        id="morning_trend_report",
        name="Morning US Trend Report at 9AM",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(hour=15, minute=0, timezone=tz),
        id="afternoon_trend_report",
        name="Afternoon US Trend Report at 3PM",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started — trend reports at 9:00 AM and 3:00 PM {Config.SCHEDULER_TIMEZONE}"
    )

    from dashboard.app import app
    port = Config.DASHBOARD_PORT
    logger.info(f"Dashboard available at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start()
