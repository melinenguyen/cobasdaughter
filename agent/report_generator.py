"""Persists the AI-analyzed report as JSON and renders the HTML page."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def save(report_data: dict[str, Any], reports_dir: str = "reports") -> dict[str, str]:
    """Save the report JSON and render the HTML file. Returns file paths."""
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    date_str = report_data.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    # Include hour so AM and PM reports don't overwrite each other
    hour_str = datetime.utcnow().strftime("%H")
    slot = "am" if int(hour_str) < 12 else "pm"
    base_name = f"trend_report_{date_str}_{slot}"

    json_path = os.path.join(reports_dir, f"{base_name}.json")
    html_path = os.path.join(reports_dir, f"{base_name}.html")

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Report JSON saved: {json_path}")

    # Render HTML using Jinja2 template
    try:
        template_dir = Path(__file__).parent.parent / "dashboard" / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
        template = env.get_template("report.html")
        html = template.render(report=report_data)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Report HTML saved: {html_path}")

    except Exception as e:
        logger.error(f"HTML render error: {e}")
        html_path = ""

    # Update "latest" symlink / copy
    latest_json = os.path.join(reports_dir, "latest.json")
    latest_html = os.path.join(reports_dir, "latest.html")
    try:
        with open(json_path, "r") as src, open(latest_json, "w") as dst:
            dst.write(src.read())
        if html_path:
            with open(html_path, "r") as src, open(latest_html, "w") as dst:
                dst.write(src.read())
    except Exception as e:
        logger.warning(f"Could not update latest files: {e}")

    return {"json": json_path, "html": html_path}


def list_reports(reports_dir: str = "reports") -> list[dict[str, str]]:
    """Return metadata for all saved reports, newest first."""
    path = Path(reports_dir)
    if not path.exists():
        return []

    reports = []
    for f in sorted(path.glob("trend_report_*.json"), reverse=True):
        try:
            with open(f) as fh:
                data = json.load(fh)
            reports.append({
                "date": data.get("report_date", f.stem.replace("trend_report_", "")),
                "filename": f.name,
                "executive_summary": data.get("executive_summary", "")[:200],
                "trend_count": len(data.get("top_trends", [])),
            })
        except Exception:
            pass

    return reports


def load_report(date_str: str, reports_dir: str = "reports") -> dict[str, Any] | None:
    """Load a specific report by date string (YYYY-MM-DD)."""
    path = Path(reports_dir) / f"trend_report_{date_str}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)
