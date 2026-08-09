"""Persists the AI-analyzed report as JSON and renders the HTML page."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Reports are written twice a day and suffixed with the slot they ran in.
SLOTS = ("am", "pm")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# 2026-05-27 to 2026-08-09 was archived as HTML only (a blanket *.json gitignore
# rule dropped the JSON before it could be committed). These pull the summary and
# trend count back out of the rendered page so those days still show on the index.
_HERO_RE = re.compile(r'<p class="hero-text">(.*?)</p>', re.S)
_COUNT_RE = re.compile(r'<span class="count-badge">(\d+)</span>')


def save(report_data: dict[str, Any], reports_dir: str = "reports") -> dict[str, str]:
    """Save the report JSON and render the HTML file. Returns file paths."""
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    date_str = report_data.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    # Use GMT+7 to label am/pm correctly
    gmt7_hour = (datetime.utcnow().hour + 7) % 24
    slot = "am" if gmt7_hour < 12 else "pm"
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


def _split_stem(stem: str) -> tuple[str, str]:
    """Split a report filename stem into (date, slot).

    Slot is "" for the un-suffixed names written before twice-daily runs began
    (2026-05-10 and earlier).
    """
    rest = stem[len("trend_report_"):] if stem.startswith("trend_report_") else stem
    date_str, _, slot = rest.partition("_")
    return date_str, slot


def _candidates(
    date_str: str, reports_dir: str, ext: str, slot: str | None = None
) -> list[Path]:
    """Report files for a date, newest slot first: pm, then am, then legacy.

    Ordering falls out of a reverse lexicographic sort, since "_pm" > "_am" > ".".
    A malformed date yields [] rather than globbing on caller-supplied text, and
    an explicit slot pins one file with no fallback to the other half of the day.
    """
    if not _DATE_RE.fullmatch(date_str):
        return []
    if slot is None:
        return sorted(Path(reports_dir).glob(f"trend_report_{date_str}*.{ext}"), reverse=True)
    if slot in SLOTS:
        return [Path(reports_dir) / f"trend_report_{date_str}_{slot}.{ext}"]
    return []


def report_paths(date_str: str, reports_dir: str = "reports") -> list[Path]:
    """Every report JSON for a date, newest slot first."""
    return _candidates(date_str, reports_dir, "json")


def _meta_from_html(text: str) -> tuple[str, int]:
    """Recover (executive_summary, trend_count) from a rendered report page.

    Reads back only what the template printed, so a template change degrades this
    to ("", 0) rather than producing wrong values.
    """
    hero = _HERO_RE.search(text)
    summary = " ".join(unescape(hero.group(1)).split()) if hero else ""
    count = _COUNT_RE.search(text)
    return summary, int(count.group(1)) if count else 0


def list_reports(reports_dir: str = "reports") -> list[dict[str, Any]]:
    """Return metadata for all saved reports, newest first (pm before am in a day).

    Includes days archived as HTML only, which would otherwise be invisible on
    the dashboard even though the rendered page is sitting right there.
    """
    path = Path(reports_dir)
    if not path.exists():
        return []

    entries: dict[str, dict[str, Any]] = {}

    for f in path.glob("trend_report_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        file_date, slot = _split_stem(f.stem)
        entries[f.stem] = {
            "date": data.get("report_date") or file_date,
            "slot": slot,
            "filename": f.name,
            "executive_summary": data.get("executive_summary", "")[:200],
            "trend_count": len(data.get("top_trends", [])),
            "has_json": True,
        }

    for f in path.glob("trend_report_*.html"):
        if f.stem in entries:
            continue
        try:
            summary, trend_count = _meta_from_html(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        file_date, slot = _split_stem(f.stem)
        entries[f.stem] = {
            "date": file_date,
            "slot": slot,
            "filename": f.name,
            "executive_summary": summary[:200],
            "trend_count": trend_count,
            "has_json": False,
        }

    return [entries[stem] for stem in sorted(entries, reverse=True)]


def load_report_html(
    date_str: str,
    reports_dir: str = "reports",
    slot: str | None = None,
) -> str | None:
    """Return the rendered HTML page for a date, for days with no JSON left."""
    for path in _candidates(date_str, reports_dir, "html", slot):
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def load_report(
    date_str: str,
    reports_dir: str = "reports",
    slot: str | None = None,
) -> dict[str, Any] | None:
    """Load a report by date string (YYYY-MM-DD).

    ``save()`` suffixes filenames with the am/pm slot, so a bare
    ``trend_report_<date>.json`` only exists for reports written before
    twice-daily runs began. With no ``slot`` this returns the newest report for
    the day — pm, else am, else the legacy un-suffixed file. Pass
    ``slot="am"``/``"pm"`` to pin one exactly; a missing slot is not backfilled
    from the other half of the day.
    """
    for path in _candidates(date_str, reports_dir, "json", slot):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None
