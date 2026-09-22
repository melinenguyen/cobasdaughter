"""Flask dashboard for viewing trend reports."""

import json
import logging
import os
import sys
import threading
import hmac
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.config import Config
from agent import report_generator
from agent.brand_pulse import PulseStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = Config.FLASK_SECRET_KEY

REPORTS_DIR = Config.REPORTS_DIR
PULSE_PLATFORMS = ("google", "instagram", "reddit", "tiktok", "web")


@app.before_request
def protect_brand_pulse():
    if request.path == '/brand-pulse' or request.path.startswith('/api/brand-pulse/'):
        password = os.getenv('BRAND_PULSE_PASSWORD', '')
        if not password:
            return 'Brand Pulse is awaiting private access configuration.', 503
        auth = request.authorization
        if not auth or not hmac.compare_digest(auth.username or '', 'coba') or not hmac.compare_digest(auth.password or '', password):
            return 'Please sign in.', 401, {'WWW-Authenticate': 'Basic realm="Brand Pulse"'}


@app.after_request
def private_pulse_response(response):
    if request.path == '/brand-pulse' or request.path.startswith('/api/brand-pulse/'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route("/")
def index():
    reports = report_generator.list_reports(REPORTS_DIR)
    return render_template("index.html", reports=reports)


@app.route("/report/<date_str>")
def view_report(date_str: str):
    # ?slot=am|pm picks one half of the day; absent means newest for that date.
    slot = request.args.get("slot")
    report = report_generator.load_report(date_str, REPORTS_DIR, slot=slot)
    if report is not None:
        return render_template("report.html", report=report)

    # 2026-05-27 to 2026-08-09 was archived as HTML only — serve the page as it
    # was rendered on the day rather than 404ing.
    html = report_generator.load_report_html(date_str, REPORTS_DIR, slot=slot)
    if html is None:
        abort(404)
    return html


@app.route("/report/latest")
def latest_report():
    reports = report_generator.list_reports(REPORTS_DIR)
    if not reports:
        return redirect(url_for("index"))
    newest = reports[0]
    return redirect(
        url_for("view_report", date_str=newest["date"], slot=newest["slot"] or None)
    )


def _pulse_request_args():
    """Validate dashboard filters before they reach SQL queries."""
    try:
        end = date.fromisoformat(request.args.get("to", date.today().isoformat()))
        start = date.fromisoformat(request.args.get("from", (end - timedelta(days=29)).isoformat()))
    except ValueError:
        abort(400, "Dates must use YYYY-MM-DD.")
    if start > end or (end - start).days > 1826:
        abort(400, "Choose a date range between one day and five years.")
    requested = [item.strip().lower() for item in request.args.get("platforms", "").split(",") if item.strip()]
    platforms = [platform for platform in requested if platform in PULSE_PLATFORMS] or list(PULSE_PLATFORMS)
    return start, end, platforms


def _comparison_range(start: date, end: date, comparison: str):
    days = (end - start).days + 1
    if comparison == "week":
        previous_sunday = start - timedelta(days=start.weekday() + 1)
        return previous_sunday - timedelta(days=6), previous_sunday
    if comparison == "month":
        previous_month_end = start.replace(day=1) - timedelta(days=1)
        return previous_month_end.replace(day=1), previous_month_end
    if comparison == "quarter":
        quarter_start_month = ((start.month - 1) // 3) * 3 + 1
        previous_quarter_end = date(start.year, quarter_start_month, 1) - timedelta(days=1)
        previous_quarter_start_month = ((previous_quarter_end.month - 1) // 3) * 3 + 1
        return date(previous_quarter_end.year, previous_quarter_start_month, 1), previous_quarter_end
    if comparison == "year":
        def previous_year(day):
            try:
                return day.replace(year=day.year - 1)
            except ValueError:
                return day.replace(year=day.year - 1, day=28)
        return previous_year(start), previous_year(end)
    previous_end = start - timedelta(days=1)
    return previous_end - timedelta(days=days - 1), previous_end


def _percent_change(current, prior):
    if current is None or not prior:
        return None
    return round(((current - prior) / prior) * 100, 1)


@app.route("/brand-pulse")
def brand_pulse():
    return render_template("brand_pulse.html")


@app.route("/api/brand-pulse/summary")
def brand_pulse_summary():
    start, end, platforms = _pulse_request_args()
    comparison = request.args.get("compare", "previous")
    if comparison not in {"previous", "week", "month", "quarter", "year"}:
        abort(400, "Unknown comparison period.")
    compared_start, compared_end = _comparison_range(start, end, comparison)
    store = PulseStore()
    current = store.aggregate(start, end, platforms)
    prior = store.aggregate(compared_start, compared_end, platforms)
    freshness = store.freshness()
    store.close()
    return jsonify({
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "comparison": {"type": comparison, "from": compared_start.isoformat(), "to": compared_end.isoformat()},
        "platforms": platforms,
        "metrics": current,
        "changes": {key: _percent_change(current[key], prior[key]) for key in current},
        "freshness": freshness,
    })


@app.route("/api/brand-pulse/trend")
def brand_pulse_trend():
    start, end, platforms = _pulse_request_args()
    store = PulseStore()
    rows = store.trend(start, end, platforms)
    store.close()
    return jsonify({"range": {"from": start.isoformat(), "to": end.isoformat()}, "rows": rows})


@app.route("/api/brand-pulse/platforms")
def brand_pulse_platforms():
    start, end, platforms = _pulse_request_args()
    store = PulseStore()
    rows = store.platform_breakdown(start, end, platforms)
    store.close()
    return jsonify({"rows": rows})


@app.route("/api/brand-pulse/mentions")
def brand_pulse_mentions():
    start, end, platforms = _pulse_request_args()
    limit = min(max(request.args.get("limit", 30, type=int), 1), 100)
    store = PulseStore()
    rows = store.recent_mentions(start, end, platforms, limit)
    store.close()
    return jsonify({"rows": rows})


@app.route("/api/brand-pulse/freshness")
def brand_pulse_freshness():
    store = PulseStore()
    rows = store.freshness()
    store.close()
    return jsonify({"rows": rows})


@app.route("/report/<date_str>/json")
def download_report_json(date_str: str):
    report = report_generator.load_report(
        date_str, REPORTS_DIR, slot=request.args.get("slot")
    )
    if report is None:
        abort(404)
    return jsonify(report)


@app.route("/run")
def trigger_run():
    """Manually trigger a trend collection run in the background."""
    def _run():
        try:
            from agent.main import run_agent
            run_agent()
        except Exception as e:
            logger.error(f"Manual run failed: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return """
    <!DOCTYPE html><html><head>
    <meta http-equiv="refresh" content="120;url=/" />
    <style>body{background:#0a0a0f;color:#e8e8f0;font-family:sans-serif;display:flex;
    align-items:center;justify-content:center;min-height:100vh;flex-direction:column;gap:16px;}
    .spinner{width:40px;height:40px;border:3px solid #2a2a3a;border-top-color:#7c5cfc;
    border-radius:50%;animation:spin 0.8s linear infinite;}
    @keyframes spin{to{transform:rotate(360deg)}}
    a{color:#7c5cfc;}</style></head>
    <body>
      <div class="spinner"></div>
      <p>Collecting US trends... this takes ~2-3 minutes.</p>
      <p>You'll be redirected automatically. <a href="/">Go back</a></p>
    </body></html>
    """


@app.errorhandler(404)
def not_found(e):
    return "<h1 style='color:#e8e8f0;font-family:sans-serif;padding:40px'>Report not found</h1>", 404


if __name__ == "__main__":
    port = Config.DASHBOARD_PORT
    logger.info(f"Starting TrendPulse dashboard on http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
