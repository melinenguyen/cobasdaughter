"""Isolated hosting entry point. Never imports the legacy email/report app."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlencode, urlparse

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
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})
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
    return {"status": "ok"}


@app.get("/")
def home():
    return page("Brand Pulse", "<p>A private measurement tool for CoBa’s Daughter’s authorized social accounts.</p>"
        "<p>The TikTok integration is in setup. It requests profile identity, account statistics and public videos "
        "from accounts whose owners authorize access. It does not publish posts or read private messages.</p>"
        "<p>This connection does not provide platform-wide earned mentions. Daily collection and the reporting dashboard "
        "are not enabled on this service yet.</p>")


@app.get("/setup")
def setup():
    if not authorized():
        return challenge()
    if not app.secret_key:
        return page("Setup needed", "<p>Configure the session key in hosting settings.</p>", 503)
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
    return page("Connection setup", body)


@app.post("/connect/tiktok")
def connect():
    if not authorized():
        return challenge()
    expected = session.pop("form_token", "")
    if not expected or not hmac.compare_digest(expected, request.form.get("csrf", "")):
        return page("Please retry", '<p>Open <a href="/setup">private setup</a> again.</p>', 400)
    if not all(os.getenv(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "BRAND_PULSE_DATABASE_URL", "BRAND_PULSE_TOKEN_KEY")):
        return page("Setup needed", "<p>Connection settings are incomplete.</p>", 503)
    state = secrets.token_urlsafe(32)
    session["tiktok_state"] = state
    session["tiktok_started"] = time.time()
    params = {"client_key": os.environ["TIKTOK_CLIENT_KEY"], "response_type": "code",
        "scope": "user.info.basic,user.info.stats,video.list", "state": state,
        "redirect_uri": origin() + "/oauth/tiktok/callback"}
    return redirect("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params))


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
