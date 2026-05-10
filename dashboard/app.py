"""Flask dashboard for viewing trend reports."""

import json
import logging
import os
import sys
import threading
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, url_for

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.config import Config
from agent import report_generator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = Config.FLASK_SECRET_KEY

REPORTS_DIR = Config.REPORTS_DIR


@app.route("/")
def index():
    reports = report_generator.list_reports(REPORTS_DIR)
    return render_template("index.html", reports=reports)


@app.route("/report/<date_str>")
def view_report(date_str: str):
    report = report_generator.load_report(date_str, REPORTS_DIR)
    if report is None:
        abort(404)
    return render_template("report.html", report=report)


@app.route("/report/latest")
def latest_report():
    reports = report_generator.list_reports(REPORTS_DIR)
    if not reports:
        return redirect(url_for("index"))
    return redirect(url_for("view_report", date_str=reports[0]["date"]))


@app.route("/report/<date_str>/json")
def download_report_json(date_str: str):
    report = report_generator.load_report(date_str, REPORTS_DIR)
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
