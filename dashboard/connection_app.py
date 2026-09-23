"""Isolated hosting entry point. Never imports the legacy email/report app."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlencode, urlparse, quote
from datetime import date, timedelta

import psycopg
import requests
from cryptography.fernet import Fernet
from flask import Flask, Response, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("BRAND_PULSE_SESSION_KEY")
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=16384)

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} · CoBa's Daughter Brand Pulse</title>
<style>body{font:17px/1.65 system-ui;margin:0;background:#f5f7fa;color:#182633}
main{max-width:760px;margin:8vh auto;padding:32px}h1{line-height:1.15;font-size:38px}
a{color:#175c87}section{background:white;padding:24px;border:1px solid #d8e0e7;border-radius:12px}
button{font:inherit;padding:12px 18px;background:#182633;color:white;border:0;border-radius:6px;cursor:pointer}
code{overflow-wrap:anywhere}small{color:#506171}</style><main>
<small>COBA'S DAUGHTER / BRAND PULSE</small><h1>{{ title }}</h1>
<section>{{ body|safe }}</section><p><a href="/">About</a> · <a href="/setup">Private setup</a></p>
</main></html>"""


def page(title, body, status=200):
    return render_template_string(PAGE, title=title, body=body), status


@app.after_request
def protect(response):
    response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://www.tiktok.com https://accounts.google.com; base-uri 'none'; frame-ancestors 'none'"})
    return response


def origin():
    value = os.getenv("BRAND_PULSE_PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL", "")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Configure the official HTTPS origin")
    return value.rstrip("/")


def authorized():
    auth = request.authorization
    expected = os.getenv("BRAND_PULSE_PASSWORD", "")
    return bool(expected and auth and auth.username == "coba" and
                hmac.compare_digest(auth.password or "", expected))


def challenge():
    return Response("Private setup. Use the administrator credentials from hosting settings.",
                    401, {"WWW-Authenticate": 'Basic realm="Brand Pulse setup"'})


@app.get("/health")
def health():
    return {"status": "ok", "version": "dashboard-preview-v1"}


@app.get("/")
def home():
    return page("Brand Pulse", "<p>A private measurement tool for CoBa’s Daughter’s authorized social accounts.</p>"
        "<p>The TikTok integration is in setup. It requests profile identity, account statistics and public videos "
        "from accounts whose owners authorize access. It does not publish posts or read private messages.</p>"
        "<p>This connection does not provide platform-wide earned mentions. Daily collection and the reporting dashboard "
        "are not enabled on this service yet.</p><p><a href='/brand-pulse'>Open private dashboard</a></p>")


@app.get("/setup")
def setup():
    if not authorized():
        return challenge()
    if not app.secret_key:
        return page("Setup needed", "<p>Configure the session key in hosting settings.</p>", 503)
    # Keep a browser-bound token stable across reloads/tabs. Rotating on every
    # GET invalidated forms still open in the user's other setup tab.
    if "form_token" not in session:
        session["form_token"] = secrets.token_urlsafe(32)
    try:
        callback = origin() + "/oauth/tiktok/callback"
    except ValueError:
        return page("Setup needed", "<p>Configure the public HTTPS address in hosting settings.</p>", 503)
    configured = all(os.getenv(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "BRAND_PULSE_DATABASE_URL", "BRAND_PULSE_TOKEN_KEY"))
    # Render dynamic content separately so all values remain HTML-escaped.
    body = render_template_string("""<p>TikTok redirect URI: <code>{{ callback }}</code></p>
    {% if configured %}<p>Before connecting, register this exact URI in the TikTok sandbox and add the authorized account as a target user.</p>
    <form method="post" action="/connect/tiktok"><input type="hidden" name="csrf" value="{{ csrf }}">
    <button>Connect authorized TikTok account</button></form>
    {% else %}<p>Hosting is ready. Add the TikTok sandbox client key and client secret in the host’s environment settings. Never paste them into chat.</p>{% endif %}
    <p>Only the account owner should approve access, on a company-approved device.</p>""",
        callback=callback, configured=configured, csrf=session["form_token"])
    google_ready = all(os.getenv(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "BRAND_PULSE_DATABASE_URL", "BRAND_PULSE_TOKEN_KEY"))
    body += render_template_string("""<hr><h2>Google Search Console</h2>
    <p>Connect the Google account that can already view cobasdaughter.com search performance.
    Read-only access; no ownership changes or service-account invitation.</p>
    <p>Google redirect URI: <code>{{ callback }}</code></p>
    {% if ready %}<form method="post" action="/connect/google">
    <input type="hidden" name="csrf" value="{{ csrf }}"><button>Connect Google — read only</button></form>
    {% else %}<p>Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in hosting settings to enable this connection.</p>{% endif %}
    <p>External Google apps in Testing usually require reauthorization after seven days.
    Connecting does not enable daily collection automatically.</p>""", ready=google_ready,
        callback=origin() + "/oauth/google/callback", csrf=session["form_token"])
    return page("Connection setup", body)


@app.post("/connect/tiktok")
def connect():
    if not authorized():
        return challenge()
    expected = session.get("form_token", "")
    if not expected:
        return page("Browser session unavailable", '<p>The browser did not return a valid session cookie. '
            'Open this site directly in Safari or Chrome on the approved device and allow cookies for this site. '
            'Do not change your passwords or API keys.</p><p>If this continues in a normal browser, '
            'the administrator should check that the hosting session key is stable.</p>'
            '<p><a href="/setup">Open private setup</a></p>', 400)
    if not hmac.compare_digest(expected, request.form.get("csrf", "")):
        return page("Setup page is out of date", '<p>Another session replaced this form. '
            'Close other setup tabs and <a href="/setup">open private setup</a> once.</p>', 400)
    if not all(os.getenv(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "BRAND_PULSE_DATABASE_URL", "BRAND_PULSE_TOKEN_KEY")):
        return page("Setup needed", "<p>Connection settings are incomplete.</p>", 503)
    state = secrets.token_urlsafe(32)
    session["tiktok_state"] = state
    session["tiktok_started"] = time.time()
    params = {"client_key": os.environ["TIKTOK_CLIENT_KEY"], "response_type": "code",
        "scope": "user.info.basic,user.info.stats,video.list", "state": state,
        "redirect_uri": origin() + "/oauth/tiktok/callback"}
    return redirect("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params), code=303)


@app.get("/oauth/tiktok/callback")
def callback():
    state = session.pop("tiktok_state", "")
    started = session.pop("tiktok_started", 0)
    if not state or not hmac.compare_digest(state, request.args.get("state", "")) or time.time() - started > 600:
        return page("Connection not accepted", "<p>The login session is missing or expired. Start again from private setup.</p>", 400)
    if request.args.get("error") or not request.args.get("code"):
        return page("Not connected", "<p>Authorization was cancelled or incomplete. No connection was saved.</p>", 400)
    try:
        response = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "code": request.args["code"], "grant_type": "authorization_code",
            "redirect_uri": origin() + "/oauth/tiktok/callback"}, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if not all(payload.get(k) for k in ("access_token", "refresh_token", "open_id")):
            raise ValueError("Incomplete authorization")
        key = base64.urlsafe_b64encode(hashlib.sha256(os.environ["BRAND_PULSE_TOKEN_KEY"].encode()).digest())
        encrypted = Fernet(key).encrypt(json.dumps(payload).encode()).decode()
        with psycopg.connect(os.environ["BRAND_PULSE_DATABASE_URL"], connect_timeout=15) as db:
            with db.cursor() as cursor:
                cursor.execute("""CREATE TABLE IF NOT EXISTS pulse_oauth_connections (
                    provider TEXT NOT NULL, account_id TEXT NOT NULL, encrypted_tokens TEXT NOT NULL,
                    updated_at DOUBLE PRECISION NOT NULL, PRIMARY KEY(provider, account_id))""")
                cursor.execute("""INSERT INTO pulse_oauth_connections VALUES (%s,%s,%s,%s)
                    ON CONFLICT(provider,account_id) DO UPDATE SET
                    encrypted_tokens=EXCLUDED.encrypted_tokens, updated_at=EXCLUDED.updated_at""",
                    ("tiktok", payload["open_id"], encrypted, time.time()))
        # Remove the short-lived authorization code from the displayed address.
        session["connected"] = True
        return redirect("/connected", code=303)
    except Exception:
        return page("Connection not saved", "<p>Check the sandbox credentials, redirect URI and database settings. No sensitive error details are displayed.</p>", 502)


@app.get("/connected")
def connected():
    if not session.pop("connected", False):
        return redirect("/setup")
    return page("TikTok authorization saved", "<p>Your authorization was stored encrypted in the private database. "
        "Video collection still needs to be enabled and tested. You can revoke access in TikTok’s app permissions.</p>")


GOOGLE_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


@app.post("/connect/google")
def connect_google():
    if not authorized():
        return challenge()
    expected = session.get("form_token", "")
    if not expected or not hmac.compare_digest(expected, request.form.get("csrf", "")):
        return page("Setup session unavailable", '<p>Open <a href="/setup">private setup</a> in the same browser with cookies enabled.</p>', 400)
    if not all(os.getenv(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "BRAND_PULSE_DATABASE_URL", "BRAND_PULSE_TOKEN_KEY")):
        return page("Google setup needed", "<p>Add the Google connection settings in Render.</p>", 503)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    session.update(google_state=state, google_started=time.time(), google_verifier=verifier)
    challenge_value = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": os.environ["GOOGLE_CLIENT_ID"], "redirect_uri": origin() + "/oauth/google/callback",
        "response_type": "code", "scope": GOOGLE_SCOPE, "access_type": "offline",
        "prompt": "consent select_account", "state": state,
        "code_challenge": challenge_value, "code_challenge_method": "S256"}), code=303)


@app.get("/oauth/google/callback")
def google_callback():
    state = session.pop("google_state", "")
    started = session.pop("google_started", 0)
    verifier = session.pop("google_verifier", "")
    if not state or not verifier or not hmac.compare_digest(state, request.args.get("state", "")) or time.time() - started > 600:
        return page("Google connection not accepted", "<p>The browser session is missing or expired. Start again from private setup.</p>", 400)
    if request.args.get("error") or not request.args.get("code"):
        return page("Google not connected", "<p>Authorization was cancelled or not granted. No connection was saved.</p>", 400)
    stage = "Google token exchange"
    try:
        result = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"], "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": origin() + "/oauth/google/callback", "grant_type": "authorization_code",
            "code": request.args["code"], "code_verifier": verifier}, timeout=25)
        result.raise_for_status()
        tokens = result.json()
        if not tokens.get("access_token") or not tokens.get("refresh_token") or GOOGLE_SCOPE not in tokens.get("scope", "").split():
            return page("Google permission incomplete", "<p>Read-only Search Console access and offline authorization are required. Reconnect and approve that permission.</p>", 400)
        stage = "Search Console performance access"
        site = os.getenv("GSC_SITE_URL", "sc-domain:cobasdaughter.com")
        # Actually query the target property before claiming that access works.
        end = date.today() - timedelta(days=3)
        check = requests.post("https://www.googleapis.com/webmasters/v3/sites/" + quote(site, safe="") + "/searchAnalytics/query",
            headers={"Authorization": "Bearer " + tokens["access_token"]},
            json={"startDate": (end - timedelta(days=6)).isoformat(), "endDate": end.isoformat(), "rowLimit": 1}, timeout=25)
        if check.status_code in (401, 403):
            return page("Google access needs attention", "<p>No connection was saved. Confirm the Search Console API is enabled in your Google Cloud project and that the selected Google account can read this exact property.</p>", 403)
        check.raise_for_status()
        stage = "encrypted database storage"
        tokens["site_url"] = site
        tokens["obtained_at"] = time.time()
        key = base64.urlsafe_b64encode(hashlib.sha256(os.environ["BRAND_PULSE_TOKEN_KEY"].encode()).digest())
        encrypted = Fernet(key).encrypt(json.dumps(tokens).encode()).decode()
        with psycopg.connect(os.environ["BRAND_PULSE_DATABASE_URL"], connect_timeout=15) as db:
            with db.cursor() as cursor:
                cursor.execute("""CREATE TABLE IF NOT EXISTS pulse_oauth_connections (
                    provider TEXT NOT NULL, account_id TEXT NOT NULL, encrypted_tokens TEXT NOT NULL,
                    updated_at DOUBLE PRECISION NOT NULL, PRIMARY KEY(provider, account_id))""")
                cursor.execute("""INSERT INTO pulse_oauth_connections VALUES (%s,%s,%s,%s)
                    ON CONFLICT(provider,account_id) DO UPDATE SET encrypted_tokens=EXCLUDED.encrypted_tokens,
                    updated_at=EXCLUDED.updated_at""", ("google_search_console", site, encrypted, time.time()))
        session["google_connected"] = True
        return redirect("/connected/google", code=303)
    except Exception:
        # Only a fixed stage name is exposed, never provider errors or tokens.
        return page("Google connection not saved", render_template_string("<p>The connection failed at {{ stage }}. No sensitive error details are displayed.</p>", stage=stage), 502)


@app.get("/connected/google")
def google_connected():
    if not session.pop("google_connected", False):
        return redirect("/setup")
    return page("Google authorization saved", "<p>Read-only access to the configured Search Console property's performance API was tested successfully. Authorization is stored encrypted.</p><p>Daily collection still needs to be enabled. No Search Console users or settings were changed.</p>")


def preview_comparison(start, end, mode):
    if mode == "year":
        def previous(day):
            try:
                return day.replace(year=day.year - 1)
            except ValueError:
                return day.replace(year=day.year - 1, day=28)
        return previous(start), previous(end)
    if mode == "week":
        last = start - timedelta(days=start.weekday() + 1)
        return last - timedelta(days=6), last
    if mode in ("month", "quarter"):
        month = start.month if mode == "month" else ((start.month - 1) // 3) * 3 + 1
        last = date(start.year, month, 1) - timedelta(days=1)
        first_month = last.month if mode == "month" else ((last.month - 1) // 3) * 3 + 1
        return date(last.year, first_month, 1), last
    return start - timedelta(days=(end - start).days + 1), start - timedelta(days=1)


@app.get("/brand-pulse")
def live_dashboard():
    if not authorized():
        return challenge()
    try:
        end = date.fromisoformat(request.args.get("to", date.today().isoformat()))
        start = date.fromisoformat(request.args.get("from", (end - timedelta(days=29)).isoformat()))
        mode = request.args.get("compare", "previous")
        if start > end or (end - start).days > 1826 or mode not in ("previous", "week", "month", "quarter", "year"):
            raise ValueError()
    except ValueError:
        return page("Invalid dates", "<p>Choose a valid date range up to five years.</p>", 400)
    prior_start, prior_end = preview_comparison(start, end, mode)
    try:
        with psycopg.connect(os.environ["BRAND_PULSE_DATABASE_URL"], connect_timeout=15) as db:
            with db.cursor() as cursor:
                cursor.execute("SELECT to_regclass('pulse_owned_instagram_snapshots'), to_regclass('pulse_oauth_connections')")
                snapshots_table, connections_table = cursor.fetchone()
                connections = []
                if connections_table:
                    cursor.execute("SELECT DISTINCT provider FROM pulse_oauth_connections")
                    connections = [row[0] for row in cursor.fetchall()]
                periods = []
                for first, last in ((start, end), (prior_start, prior_end)):
                    if not snapshots_table:
                        periods.append((0, None, None, None))
                        continue
                    cursor.execute("""SELECT COUNT(*), SUM(likes), SUM(comments), MAX(observed_at)
                        FROM (SELECT DISTINCT ON (account_id, media_id) media_id, likes, comments, observed_at
                        FROM pulse_owned_instagram_snapshots
                        WHERE substring(observed_at,1,10) >= %s AND substring(observed_at,1,10) <= %s
                        ORDER BY account_id, media_id, observed_at DESC) latest""", (first.isoformat(), last.isoformat()))
                    periods.append(cursor.fetchone())
        current, prior = periods
        # Snapshot samples are not a complete media inventory. Never calculate
        # growth from differently sampled sets of posts.
        body = render_template_string("""<p><b>Limited preview · Daily collection is not enabled</b></p>
        <form method="get"><p><label>From <input name="from" type="date" value="{{ start }}" required></label>
        <label>To <input name="to" type="date" value="{{ end }}" required></label></p>
        <p><label>Compare with <select name="compare">{% for value,label in choices %}
        <option value="{{ value }}" {% if value == mode %}selected{% endif %}>{{ label }}</option>{% endfor %}</select></label>
        <button>Apply dates</button></p></form>
        <h2>Instagram — stored test sample</h2>
        <p>Dates filter when snapshots were collected, not when posts were published. Likes and comments are lifetime counts at collection, not activity within the period.</p>
        <div style="overflow-x:auto"><table style="width:100%;text-align:left"><thead><tr><th>Metric</th><th>Selected period</th><th>Comparison period</th></tr></thead>
        <tbody>{% for label,index in [('Sampled posts',0),('Likes on sampled posts',1),('Comments on sampled posts',2)] %}
        <tr><td>{{ label }}</td><td>{{ current[index] if current[0] and current[index] is not none else 'Unavailable' }}</td>
        <td>{{ prior[index] if prior[0] and prior[index] is not none else 'Unavailable' }}</td></tr>{% endfor %}</tbody></table></div>
        <p>Comparison: {{ prior_start }} – {{ prior_end }}. Growth percentages are withheld because the samples may contain different posts.</p>
        <p>Latest snapshot in selected period: {{ current[3] or 'Unavailable' }}</p>
        <h2>Source status</h2><ul>
        <li>Instagram: {{ 'stored sample available' if snapshots_table else 'no stored sample yet' }}; ongoing collection not enabled.</li>
        <li>TikTok: {{ 'authorization stored; collection not enabled' if 'tiktok' in connections else 'not connected' }}.</li>
        <li>Google Search Console: {{ 'authorization stored; collection not enabled' if 'google_search_console' in connections else 'not connected' }}.</li>
        <li>Reddit and public web mentions: not connected.</li></ul>
        <p>Earned mentions, reach, sentiment and total brand search volume are unavailable. This dashboard does not imply zero mentions or complete coverage.</p>
        <p><a href="/setup">Manage connections</a></p>""", start=start, end=end, mode=mode,
            choices=[("previous", "Last comparable period"), ("week", "Previous completed week"), ("month", "Previous completed month"), ("quarter", "Previous completed quarter"), ("year", "Same dates last year")],
            current=current, prior=prior, prior_start=prior_start, prior_end=prior_end,
            snapshots_table=snapshots_table, connections=connections)
        return page("Brand Pulse dashboard", body)
    except Exception:
        return page("Data temporarily unavailable", "<p>The private database could not be read. No credentials or sensitive error details are displayed.</p>", 503)
