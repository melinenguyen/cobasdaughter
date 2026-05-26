"""
Main agent orchestrator.

Runs the full pipeline:
  1. Collect trends from all sources (parallel where possible)
  2. Analyze with Claude AI
  3. Save JSON + HTML report
  4. Send Slack digest
"""

import concurrent.futures
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.config import Config
from agent.collectors import google_trends, reddit, twitter, youtube, news, instagram, cultural_calendar, brand_intel
from agent import analyzer, report_generator, slack_notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trend_agent")


def _collect_all() -> dict:
    """Run all collectors in parallel threads."""
    logger.info("Starting parallel data collection...")

    results = {}

    def _safe(name: str, fn, *args, **kwargs):
        try:
            data = fn(*args, **kwargs)
            logger.info(f"✓ {name} collected")
            return name, data
        except Exception as e:
            logger.error(f"✗ {name} failed: {e}")
            return name, {"source": name, "errors": [str(e)]}

    tasks = [
        ("google_trends", google_trends.collect),
        ("reddit", reddit.collect, Config.REDDIT_CLIENT_ID, Config.REDDIT_CLIENT_SECRET, Config.REDDIT_USER_AGENT),
        ("twitter", twitter.collect, Config.TWITTER_BEARER_TOKEN),
        ("youtube", youtube.collect, Config.YOUTUBE_API_KEY),
        ("news", news.collect),
        ("brand_intel", brand_intel.collect),
        ("instagram", instagram.collect, Config.INSTAGRAM_ACCESS_TOKEN, Config.INSTAGRAM_BUSINESS_ACCOUNT_ID),
        ("cultural_calendar", cultural_calendar.collect),
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for task in tasks:
            name = task[0]
            fn = task[1]
            args = task[2:] if len(task) > 2 else ()
            futures.append(executor.submit(_safe, name, fn, *args))

        for future in concurrent.futures.as_completed(futures):
            name, data = future.result()
            results[name] = data

    logger.info(f"Collection complete: {len(results)} sources")
    return results


def run_agent(
    dashboard_url: str = os.getenv("DASHBOARD_URL", ""),
    dry_run: bool = False,
) -> dict:
    """
    Full pipeline execution. Returns the final report dict.

    Args:
        dashboard_url: Public URL to the dashboard (included in Slack message).
        dry_run: If True, skip Slack send and just return the report.
    """
    start_time = datetime.utcnow()
    logger.info(f"=== TrendPulse Agent Starting — {start_time.strftime('%Y-%m-%d %H:%M UTC')} ===")

    # 1. Collect
    collected = _collect_all()

    # 2. Load previous report for deduplication
    previous_report = None
    latest_path = Path(Config.REPORTS_DIR) / "latest.json"
    if latest_path.exists():
        try:
            with open(latest_path) as f:
                previous_report = json.load(f)
            logger.info(f"Loaded previous report ({previous_report.get('report_date','?')}) for deduplication")
        except Exception as e:
            logger.warning(f"Could not load previous report: {e}")

    # 3. Analyze (Gemini free tier first, Anthropic as fallback)
    logger.info("Sending data to AI for analysis...")
    analysis = analyzer.analyze(
        collected,
        api_key=Config.ANTHROPIC_API_KEY,
        previous_report=previous_report,
        gemini_key=Config.GEMINI_API_KEY,
    )

    if analysis["status"] != "success":
        logger.error(f"Analysis failed: {analysis.get('error')}")
        return {"status": "error", "error": analysis.get("error")}

    report = analysis["report"]

    # 4. Save report
    logger.info("Saving report files...")
    file_paths = report_generator.save(report, Config.REPORTS_DIR)
    logger.info(f"Saved: {file_paths}")

    # Fallback report link: use GitHub repo reports folder if no dashboard URL
    github_repo = os.getenv("GITHUB_REPOSITORY", "")  # set automatically in Actions
    repo_url = f"https://github.com/{github_repo}/tree/main/reports" if github_repo else ""

    # 5. Send Slack digest
    if not dry_run:
        logger.info("Sending Slack digest...")
        slack_sent = slack_notifier.send(
            report,
            Config.SLACK_BOT_TOKEN,
            Config.SLACK_CHANNEL_ID,
            dashboard_url=dashboard_url,
            repo_url=repo_url,
        )
        if slack_sent:
            logger.info("Slack digest sent successfully")
        else:
            logger.warning("Slack digest not sent (check credentials)")
    else:
        logger.info("Dry run — Slack skipped")

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"=== Agent complete in {elapsed:.1f}s ===")

    return {
        "status": "success",
        "report_date": report.get("report_date"),
        "trend_count": len(report.get("top_trends", [])),
        "files": file_paths,
        "elapsed_seconds": elapsed,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TrendPulse US Trend Agent")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack send")
    parser.add_argument("--dashboard-url", default="", help="Dashboard public URL")
    args = parser.parse_args()

    result = run_agent(dashboard_url=args.dashboard_url, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        sys.exit(1)
