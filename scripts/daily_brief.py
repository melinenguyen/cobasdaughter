#!/usr/bin/env python3
"""
CoBa's Daughter — Daily Email War Room Brief
Runs daily at 9AM GMT+7.
Scans brand inbox → pulls Klaviyo state → generates War Room brief → posts to Slack DM + sends email.

Environment vars:
  ANTHROPIC_API_KEY        — Claude API key (required)
  DAILY_BRIEF_SLACK_TOKEN  — Slack bot token for CoBa Brief bot (preferred)
  SLACK_BOT_TOKEN          — Slack bot token fallback (TrendPulse)
  SLACK_USER_ID            — Méline's Slack user ID (default: U08V8865GD7)
  GMAIL_APP_PASSWORD       — Gmail App Password for meline.nguyen@lixibox.com
  GMAIL_TOKEN_JSON         — Gmail OAuth token, base64-encoded (optional, brand inbox scan)
  KLAVIYO_PRIVATE_API_KEY  — Klaviyo private API key (optional, live campaign context)
"""

import os
import json
import base64
import datetime
import smtplib
import re
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── CONFIG ──────────────────────────────────────────────────────────────────

REFERENCE_BRANDS = [
    {"name": "Flamingo Estate", "query": "from:flamingoestate.com newer_than:2d"},
    {"name": "Rhode",           "query": "from:rhodeskin.com newer_than:2d"},
    {"name": "OUAI",            "query": "from:theouai.com newer_than:2d"},
    {"name": "Salt & Stone",    "query": "from:saltandstone.com newer_than:2d"},
    {"name": "Nécessaire",      "query": "from:necessaire.com newer_than:2d"},
]

SLACK_USER_ID   = os.environ.get("SLACK_USER_ID", "U08V8865GD7")
EMAIL_TO        = "meline.nguyen@lixibox.com"
EMAIL_CC        = "phuonglt.job@gmail.com"

BRAND_PALETTE = {
    "dark_brown": "#2a1f17",
    "rust":       "#6b4423",
    "olive":      "#716a56",
    "beige":      "#f5f1ea",
    "cream":      "#faf8f5",
    "light_text": "#9b8b7a",
    "white":      "#ffffff",
}

# Five-email baseline — Claude updates this daily with live intel
FIVE_EMAIL_BASELINE = [
    {
        "num": 1, "send_date": "Tue May 26 · 10 AM GMT+7",
        "type": "Post-Sale Loyalty",
        "subject": "You got it. Here's how to use it.",
        "preview": "The ritual for everything you just ordered.",
        "from_email": "ritual@cobasdaughter.com",
        "angle": "Post-purchase ritual guide for 27% off buyers. Zero selling. Build loyalty.",
        "cta": "Start Your Ritual →",
        "segment": "Purchased May 25 sale · Smart Send OFF",
    },
    {
        "num": 2, "send_date": "Thu May 28 · 10 AM GMT+7",
        "type": "Re-Engage Non-Buyers",
        "subject": "the sale is gone. the skin glow isn't.",
        "preview": "You don't need a discount to start your ritual.",
        "from_email": "ritual@cobasdaughter.com",
        "angle": "Post-sale recovery. Clickers who didn't buy. No discount.",
        "cta": "Shop The Ritual",
        "segment": "Clicked May 25 email · no purchase · Smart Send ON",
    },
    {
        "num": 3, "send_date": "Sun Jun 1 · 10 AM GMT+7",
        "type": "Aloe Duo Education",
        "subject": "what aloe vera does at 2am",
        "preview": "(while you sleep, it's working.)",
        "from_email": "ritual@cobasdaughter.com",
        "angle": "Summer hydration science. Aloe Duo ingredient story. Night-repair angle.",
        "cta": "Shop The Aloe Duo",
        "segment": "Full engaged list · exclude Aloe buyers 60d · Smart Send ON",
    },
    {
        "num": 4, "send_date": "Thu Jun 5 · 10 AM GMT+7",
        "type": "Father's Day Gift Push",
        "subject": "the gift for the man who says he doesn't want anything",
        "preview": "He does. You know he does.",
        "from_email": "hi@cobasdaughter.com",
        "angle": "Father's Day June 15. Gift Bundle as the obvious answer. 10 days out.",
        "cta": "Shop The Gift Bundle",
        "segment": "Full engaged list · Smart Send ON",
    },
    {
        "num": 5, "send_date": "Tue Jun 10 · 10 AM GMT+7",
        "type": "Summer Body Prep",
        "subject": "summer bodies are made in June",
        "preview": "The 5-minute ritual. No gym required.",
        "from_email": "ritual@cobasdaughter.com",
        "angle": "Summer peak season. Scrub Duo hero. Rhode one-product format.",
        "cta": "Shop The Scrub Duo",
        "segment": "Full engaged list · Smart Send ON",
    },
]

# ─── KLAVIYO CONTEXT ─────────────────────────────────────────────────────────

def get_klaviyo_context() -> str:
    """Pull recent campaign history from Klaviyo REST API."""
    api_key = os.environ.get("KLAVIYO_PRIVATE_API_KEY")
    if not api_key:
        return "Klaviyo not connected (KLAVIYO_PRIVATE_API_KEY not set)."
    import requests
    try:
        h = {"Authorization": f"Klaviyo-API-Key {api_key}", "revision": "2024-02-15"}
        r = requests.get(
            "https://a.klaviyo.com/api/campaigns/",
            headers=h,
            params={
                "filter": "equals(messages.channel,'email')",
                "fields[campaign]": "name,status,send_time,scheduled_at",
                "fields[campaign-message]": "definition.content.subject,definition.content.preview_text",
                "include": "campaign-messages",
                "sort": "-created_at",
                "page[size]": "8",
            },
            timeout=15,
        )
        r.raise_for_status()
        result   = r.json()
        campaigns = result.get("data", [])
        included  = {i["id"]: i for i in result.get("included", [])}

        lines = []
        for c in campaigns:
            a = c.get("attributes", {})
            msg_ids = [
                m["id"] for m in
                c.get("relationships", {}).get("campaign-messages", {}).get("data", [])
            ]
            subjects = [
                included[mid].get("attributes", {}).get("definition", {}).get("content", {}).get("subject", "")
                for mid in msg_ids if mid in included
            ]
            subj = subjects[0] if subjects else "(no subject)"
            dt   = (a.get("send_time") or a.get("scheduled_at") or "")[:10]
            lines.append(f"  [{a.get('status','?')}] {dt} — \"{subj}\" ({a.get('name','?')})")

        return "Recent Klaviyo campaigns:\n" + "\n".join(lines) if lines else "No Klaviyo campaigns found."
    except Exception as e:
        return f"Klaviyo fetch failed: {e}"

# ─── GMAIL HELPERS ────────────────────────────────────────────────────────────

def build_gmail_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    token_json = os.environ.get("GMAIL_TOKEN_JSON")
    if not token_json:
        raise ValueError("GMAIL_TOKEN_JSON secret not set")
    token_data = json.loads(base64.b64decode(token_json))
    creds = Credentials.from_authorized_user_info(token_data)
    return build("gmail", "v1", credentials=creds)


def get_recent_brand_emails(service, hours_back: int = 48) -> dict:
    results = {}
    cutoff      = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    after_epoch = int(cutoff.timestamp())
    for brand in REFERENCE_BRANDS:
        query = f"({brand['query']}) after:{after_epoch}"
        try:
            resp = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
            msgs = resp.get("messages", [])
            brand_emails = []
            for ref in msgs:
                msg = service.users().messages().get(
                    userId="me", messageId=ref["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                hdrs = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                brand_emails.append({
                    "subject": hdrs.get("Subject", "(no subject)"),
                    "date":    hdrs.get("Date", ""),
                    "snippet": msg.get("snippet", "")[:200],
                })
            results[brand["name"]] = brand_emails
        except Exception as e:
            results[brand["name"]] = [{"error": str(e)}]
    return results

# ─── BRIEF GENERATOR ─────────────────────────────────────────────────────────

def generate_brief(brand_emails: dict, klaviyo_context: str, today: str) -> str:
    from anthropic import Anthropic
    client = Anthropic()

    brand_data_text = ""
    for brand_name, emails in brand_emails.items():
        brand_data_text += f"\n### {brand_name}\n"
        if not emails:
            brand_data_text += "  No emails in the last 48h.\n"
            continue
        for e in emails:
            if "error" in e:
                brand_data_text += f"  Error: {e['error']}\n"
            else:
                brand_data_text += f"  Subject: {e['subject']}\n  Snippet: {e['snippet']}\n  ---\n"

    baseline_text = ""
    for em in FIVE_EMAIL_BASELINE:
        baseline_text += f"  Email {em['num']}: {em['send_date']} — \"{em['subject']}\" — {em['type']}\n"

    prompt = textwrap.dedent(f"""
        You are the email war room strategist for CoBa's Daughter — a Vietnamese DTC body care brand.

        BRAND SNAPSHOT:
        - Launched March 2026 · ~2 500 subscribers · poor open + click rates (goal: fix both)
        - Products: Coffee Body Exfoliator (Scrub Duo) · Aloe Soothing Gel (Aloe Duo) ·
          3-in-1 Artisan Soap (Fig & Cedarwood / Grapefruit Peel & Eucalyptus / Persian Lime & Coconut) ·
          Gift Bundle Sets · Deluxe Bath & Body Care Gift Basket
        - Last sent campaign (May 25): "Up to 27% OFF Sets & Bundles" · free shipping $50+
        - Sender personas: ritual@cobasdaughter.com (founder/brand/story) · hi@cobasdaughter.com (commercial)
        - Brand voice: intimate · sensory · Vietnamese heritage · "low maintenance luxury"
        - Brand story: CoBa = Cô Ba, the iconic Saigon woman, timeless beauty wisdom passed down
        - Key product copy: "The only coffee scrub with a green tea scent" · "99% pure aloe vera" ·
          "3-in-1: hand wash / body wash / bubble bath"

        KLAVIYO CAMPAIGN HISTORY:
        {klaviyo_context}

        BRAND INBOX SCAN (last 48h from 5 reference brands):
        {brand_data_text}

        5-EMAIL BASELINE PLAN (update with live intel):
        {baseline_text}

        CALENDAR:
        - Today: {today} (Vietnam, GMT+7)
        - Memorial Day US: May 26 · Father's Day US: June 15 · Summer peak: June–July

        ══════════════════════════════════════════════
        Write EXACTLY two sections separated by this line on its own: ===EMAIL TEMPLATE===
        ══════════════════════════════════════════════

        SECTION 1 — SLACK WAR ROOM BRIEF (Slack mrkdwn · max 2 000 chars)

        :red_circle: *CoBa's Daughter — Email War Room · {today}*
        _Live Gmail scan · Klaviyo updated · 5-email plan_


        :inbox_tray: *WHAT YOUR INBOX SHOWS RIGHT NOW*
        [For each brand that sent in last 48h: 1 sentence on their angle. Lead with most interesting.]
        [If no brand sent anything: note the silence and what it means.]
        *Key pattern:* [1 sentence — dominant theme across competitor inboxes today]


        :fire: *THE OPPORTUNITY RIGHT NOW*
        [2–3 sentences: specific calendar window · what white space exists · CoBa's angle to own it]


        :white_check_mark: *YOUR 5-EMAIL PLAN — Updated {today}*

        :e-mail: *Email 1 — [date + urgency label]*
        > Subject: _"[subject line]"_
        > Product: [product name]
        > Audience: [segment · Smart Sending ON/OFF · exclude rule]
        > UTM: `[campaign-slug]`
        > Copy: "[1–2 sentence hook, CoBa voice]"
        > CTA: _[button text]_

        [Repeat for Emails 2, 3, 4, 5 — same format. Update dates/subjects based on live intel.]


        :zap: *DO RIGHT NOW — Step by step*
        Step 1 → [Klaviyo: exact menu path + specific action]
        Step 2 → [...]
        Step 3 → [...]


        :bulb: *One strategic note:* [1 sentence — what competitor tactic to steal today]


        ===EMAIL TEMPLATE===

        SECTION 2 — FULL EMAIL COPY FOR EMAIL 1 (paste into Klaviyo)

        Subject: [exact subject]
        Preview text: [exact preview]
        From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
        From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
        Segment: [exact segment]

        BODY:
        [Full email body — 150–200 words · CoBa's brand voice]
        [Opening: 1 intimate/sensory hook sentence — no "Dear", no "Hi"]
        [Body: 2–3 short paragraphs — ingredient story / ritual moment / specific product benefit]
        [Reference Vietnamese heritage or brand story subtly if relevant]
        [Closing: 1 soft CTA paragraph]
        [Sign-off: — Méline  OR  — The CoBa's Daughter team]

        CTA BUTTON: [exact button text, 2–5 words]
    """).strip()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

# ─── SLACK SENDER ─────────────────────────────────────────────────────────────

def post_to_slack(brief_text: str, today: str) -> str:
    from slack_sdk import WebClient
    # Use dedicated CoBa Brief bot first; fall back to shared TrendPulse token
    token = os.environ.get("DAILY_BRIEF_SLACK_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("DAILY_BRIEF_SLACK_TOKEN or SLACK_BOT_TOKEN not set")

    client = WebClient(token=token)
    # Only post the Slack section (before ===EMAIL TEMPLATE===)
    slack_section = brief_text.split("===EMAIL TEMPLATE===")[0].strip()
    resp = client.chat_postMessage(
        channel=SLACK_USER_ID,
        text=slack_section,
        mrkdwn=True,
    )
    return resp["ts"]

# ─── EMAIL HTML RENDERER ──────────────────────────────────────────────────────

SLACK_EMOJI_MAP = {
    ":red_circle:": "🔴", ":inbox_tray:": "📥", ":fire:": "🔥",
    ":white_check_mark:": "✅", ":e-mail:": "📧", ":zap:": "⚡",
    ":bulb:": "💡", ":warning:": "⚠️",
}


def _line_to_html(line: str, p: dict) -> str:
    for code, emoji in SLACK_EMOJI_MAP.items():
        line = line.replace(code, emoji)
    line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def fmt(l):
        l = re.sub(r"\*([^*]+)\*", r"<strong>\1</strong>", l)
        l = re.sub(r"_([^_]+)_",   r"<em>\1</em>",         l)
        l = re.sub(r"`([^`]+)`",   rf"<code style='background:#f0ece4;padding:1px 5px;border-radius:3px;font-size:11px'>\1</code>", l)
        return l

    # Blockquote (> ...) — plan detail rows
    if line.startswith("&gt; "):
        inner = fmt(line[5:])
        return (
            f"<p style='margin:2px 0 2px 12px;color:{p['olive']};font-size:12px;"
            f"border-left:2px solid {p['rust']};padding-left:8px'>{inner}</p>"
        )
    # Step lines
    if re.match(r"^Step \d", line):
        return f"<p style='margin:3px 0;font-size:12px;color:{p['dark_brown']}'>{fmt(line)}</p>"
    # Emoji section headers (e.g. 🔴 *...*  or  📥 *...*)
    if re.match(r"^[🔴📥🔥✅📧⚡💡⚠️]", line):
        return (
            f"<p style='margin:20px 0 6px;font-size:14px'>{fmt(line)}</p>"
        )
    # Empty
    if not line.strip():
        return "<div style='height:6px'></div>"
    return f"<p style='margin:4px 0;color:{p['dark_brown']};font-size:13px;line-height:1.6'>{fmt(line)}</p>"


def _render_html(brief_text: str, today: str) -> str:
    p = BRAND_PALETTE

    parts          = brief_text.split("===EMAIL TEMPLATE===")
    slack_section  = parts[0].strip()
    email_template = parts[1].strip() if len(parts) > 1 else ""

    brief_html = "\n".join(_line_to_html(l, p) for l in slack_section.split("\n"))

    # ── Parse + render the Email 1 template section ──────────────────────────
    template_html = ""
    if email_template:
        header_fields = {}
        body_lines    = []
        in_body       = False

        for line in email_template.split("\n"):
            stripped = line.strip()
            if stripped == "BODY:":
                in_body = True
                continue
            if not in_body:
                for key in ("Subject", "Preview text", "From name", "From email", "Segment", "CTA BUTTON"):
                    if stripped.startswith(key + ":"):
                        header_fields[key] = stripped[len(key) + 1:].strip()
                        break
            else:
                body_lines.append(line)

        header_rows = "".join(
            f"<tr>"
            f"<td style='padding:3px 14px 3px 0;color:{p['light_text']};font-size:11px;font-weight:600;white-space:nowrap;vertical-align:top'>{k}</td>"
            f"<td style='padding:3px 0;color:{p['dark_brown']};font-size:12px'>{v}</td>"
            f"</tr>"
            for k, v in header_fields.items() if k != "CTA BUTTON"
        )

        body_html = ""
        for para in "\n".join(body_lines).split("\n\n"):
            para = para.strip()
            if para:
                body_html += f"<p style='margin:0 0 14px;line-height:1.75;font-size:13px;color:{p['dark_brown']}'>{para}</p>"

        cta_label = header_fields.get("CTA BUTTON", "Shop Now →")

        template_html = f"""
        <div style="background:{p['cream']};padding:28px 36px 8px">
          <div style="color:{p['rust']};font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px">
            ✦ Today's Email — Full Copy Ready to Paste
          </div>
        </div>
        <div style="background:{p['cream']};padding:0 24px 28px">
          <div style="background:{p['white']};border-radius:8px;overflow:hidden;border:1px solid #e8e3da">
            <div style="background:{p['beige']};padding:14px 20px;border-bottom:1px solid #e8e3da">
              <table><tbody>{header_rows}</tbody></table>
            </div>
            <div style="padding:24px 28px 8px">
              {body_html}
            </div>
            <div style="padding:8px 28px 24px">
              <span style="display:inline-block;background:{p['dark_brown']};color:#fff;padding:11px 26px;border-radius:4px;font-size:12px;font-weight:600;letter-spacing:.5px">{cta_label}</span>
            </div>
          </div>
        </div>
        """

    # ── Priority checklist ────────────────────────────────────────────────────
    items = [
        ("🔴", "Set up <strong>ICYMI resend</strong> — 48h after each campaign to non-openers, different subject"),
        ("🔴", "Fill <strong>all preview texts</strong> — check every scheduled draft in Klaviyo now"),
        ("🔴", "Add <strong>5–10% off trigger</strong> to Abandon Cart Email 2 (steal from Nécessaire)"),
        ("🟡", "Switch FROM name to <strong>\"Méline at CoBa's Daughter\"</strong> on brand/story emails"),
        ("🟡", "Create <strong>Engaged 90-day</strong> + <strong>At-Risk 90–180-day</strong> Klaviyo segments"),
        ("🟡", "Set up <strong>Post-Purchase Review Request</strong> flow (14 days after delivery)"),
        ("🟢", "Build <strong>Browse Abandonment</strong> flow (viewed product, no cart add)"),
        ("🟢", "Build <strong>Sunset / Winback</strong> flow for 180+ day non-openers"),
        ("🟢", "Enable <strong>A/B subject line test</strong> on every future campaign"),
    ]
    checklist_rows = "".join(
        f"<tr><td style='padding:4px 8px 4px 0;font-size:14px'>{icon}</td>"
        f"<td style='padding:4px 0;font-size:12px;color:{p['dark_brown']};line-height:1.5'>{text}</td></tr>"
        for icon, text in items
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{p['beige']};font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:700px;margin:24px auto 0;border-radius:8px;overflow:hidden;box-shadow:0 2px 14px rgba(0,0,0,.09)">

  <!-- HEADER -->
  <div style="background:{p['dark_brown']};padding:28px 36px">
    <div style="color:#c9b99a;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px">CoBa's Daughter</div>
    <div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:-.3px">Email War Room Brief</div>
    <div style="color:rgba(255,255,255,.45);font-size:12px;margin-top:5px">{today} · 9:00 AM GMT+7 · Auto-generated daily</div>
  </div>

  <!-- BRIEF -->
  <div style="background:{p['white']};padding:32px 36px 24px">
    {brief_html}
  </div>

  {template_html}

  <!-- PRIORITY CHECKLIST -->
  <div style="background:{p['beige']};padding:0 36px 28px">
    <div style="background:{p['white']};border-left:3px solid {p['rust']};padding:16px 20px;border-radius:0 6px 6px 0">
      <div style="color:{p['rust']};font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">⚡ Ongoing Priority Checklist</div>
      <table style="width:100%"><tbody>{checklist_rows}</tbody></table>
    </div>
  </div>

  <!-- FOOTER -->
  <div style="background:{p['dark_brown']};padding:18px 36px;text-align:center">
    <div style="color:rgba(255,255,255,.35);font-size:11px">CoBa's Daughter · Daily Email War Room · Auto-sent 9:02 AM GMT+7</div>
  </div>

</div>
</body></html>"""

# ─── EMAIL SENDER ─────────────────────────────────────────────────────────────

def send_email_brief(brief_text: str, today: str) -> None:
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD not set — see GMAIL_APP_PASSWORD_SETUP.md")

    html_body = _render_html(brief_text, today)
    plain     = brief_text.split("===EMAIL TEMPLATE===")[0].strip()
    subject   = f"CoBa's Email War Room — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"CoBa's Daughter Brief <{EMAIL_TO}>"
    msg["To"]      = EMAIL_TO
    msg["Cc"]      = EMAIL_CC

    msg.attach(MIMEText(plain,     "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_TO, app_password)
        smtp.sendmail(EMAIL_TO, [EMAIL_TO, EMAIL_CC], msg.as_bytes())

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    vn_tz = datetime.timezone(datetime.timedelta(hours=7))
    today = datetime.datetime.now(vn_tz).strftime("%A, %B %-d, %Y")

    print(f"[daily_brief] Starting for {today}")

    # 1. Gmail inbox scan (optional)
    brand_emails = {b["name"]: [] for b in REFERENCE_BRANDS}
    try:
        service      = build_gmail_service()
        brand_emails = get_recent_brand_emails(service)
        found = sum(len(v) for v in brand_emails.values())
        print(f"[daily_brief] {found} brand emails fetched")
    except Exception as e:
        print(f"[daily_brief] Gmail fetch failed: {e}")

    # 2. Klaviyo context (optional)
    try:
        klaviyo_context = get_klaviyo_context()
        print(f"[daily_brief] Klaviyo: {len(klaviyo_context)} chars")
    except Exception as e:
        klaviyo_context = f"Klaviyo unavailable: {e}"
        print(f"[daily_brief] Klaviyo failed: {e}")

    # 3. Generate brief
    print("[daily_brief] Generating brief…")
    try:
        brief = generate_brief(brand_emails, klaviyo_context, today)
        print(f"[daily_brief] Brief ready ({len(brief)} chars)")
    except Exception as e:
        print(f"[daily_brief] Claude failed: {e}")
        brief = (
            f":warning: *CoBa's Daily Brief failed today.*\n"
            f"Error: {e}\n\n"
            f"Check ANTHROPIC_API_KEY credits at console.anthropic.com"
        )

    # 4. Slack DM
    print("[daily_brief] Posting to Slack…")
    try:
        ts = post_to_slack(brief, today)
        print(f"[daily_brief] Slack ts: {ts}")
    except Exception as e:
        print(f"[daily_brief] Slack failed: {e}")

    # 5. Email
    print(f"[daily_brief] Sending email to {EMAIL_TO} (cc {EMAIL_CC})…")
    try:
        send_email_brief(brief, today)
        print("[daily_brief] Email sent.")
    except Exception as e:
        print(f"[daily_brief] Email failed: {e}")

    print("[daily_brief] Done.")


if __name__ == "__main__":
    main()
