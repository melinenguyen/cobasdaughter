#!/usr/bin/env python3
"""
CoBa's Daughter — Daily Email War Room Brief
Runs daily at 9AM GMT+7.
Scans brand inbox (last 48h real-time) → Klaviyo context → War Room brief + 5 email templates → Slack + email.

Environment vars:
  ANTHROPIC_API_KEY        — Claude API key (required)
  DAILY_BRIEF_SLACK_TOKEN  — Slack bot token for Email Hub bot (preferred)
  SLACK_BOT_TOKEN          — Slack fallback token (TrendPulse)
  SLACK_USER_ID            — Méline's Slack user ID (default: U08V8865GD7)
  GMAIL_APP_PASSWORD       — Gmail App Password for meline.nguyen@lixibox.com
  GMAIL_TOKEN_JSON         — Gmail OAuth token base64-encoded (optional, brand inbox scan)
  KLAVIYO_PRIVATE_API_KEY  — Klaviyo private API key (optional, live campaign context)
"""

import os
import json
import base64
import datetime
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── CONFIG ──────────────────────────────────────────────────────────────────

REFERENCE_BRANDS = [
    # Gmail's from: operator matches exact domain only (not subdomains).
    # Marketing ESPs send from subdomains (email.*, mail.*, em.*) so we
    # also search the sender display name — it's reliable regardless of ESP.
    {
        "name": "Flamingo Estate",
        "query": 'in:all (from:flamingoestate.com OR from:"Flamingo Estate")',
    },
    {
        "name": "Rhode",
        "query": 'in:all (from:rhodeskin.com OR from:rhode.com OR from:"Rhode")',
    },
    {
        "name": "OUAI",
        "query": 'in:all (from:theouai.com OR from:ouai.com OR from:"OUAI")',
    },
    {
        "name": "Salt & Stone",
        "query": 'in:all (from:saltandstone.com OR from:"Salt & Stone" OR from:"SALT & STONE")',
    },
    {
        "name": "Nécessaire",
        "query": 'in:all (from:necessaire.com OR from:"Necessaire" OR from:"Nécessaire")',
    },
]

SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U08V8865GD7")
EMAIL_TO      = "meline.nguyen@lixibox.com"
EMAIL_CC      = "phuonglt.job@gmail.com"

BRAND_PALETTE = {
    "dark_brown": "#2a1f17",
    "rust":       "#6b4423",
    "olive":      "#716a56",
    "beige":      "#f5f1ea",
    "cream":      "#faf8f5",
    "light_text": "#9b8b7a",
    "white":      "#ffffff",
    "border":     "#e8e3da",
}

# Canva design: https://www.canva.com/design/DAGqEHj884k/
CANVA_DESIGN_ID = "DAGqEHj884k"

# Maps product theme → Canva design page number (1-based)
# Update these when you change the Canva design page order
CANVA_PAGES = {
    "scrub_duo":   1,
    "aloe_duo":    2,
    "soap":        3,
    "gift_bundle": 4,
    "lifestyle":   5,
    "brand_story": 6,
    "ingredients": 7,
    "ritual":      8,
    "hero":        9,
    "summer":      10,
}

# ─── CANVA IMAGE FETCHER ──────────────────────────────────────────────────────

def _get_canva_token() -> str:
    """Return a live Canva API access token. Tries refresh flow if direct token absent."""
    token = os.environ.get("CANVA_ACCESS_TOKEN", "")
    if token:
        return token
    client_id     = os.environ.get("CANVA_CLIENT_ID", "")
    client_secret = os.environ.get("CANVA_CLIENT_SECRET", "")
    refresh_token = os.environ.get("CANVA_REFRESH_TOKEN", "")
    if not (client_id and client_secret and refresh_token):
        return ""
    import requests
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            "https://api.canva.com/rest/v1/oauth/token",
            headers={"Authorization": f"Basic {creds}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("access_token", "")
    except Exception as e:
        print(f"[daily_brief] Canva token refresh failed: {e}")
        return ""


def get_canva_page_images(page_nums: list) -> dict:
    """Fetch Canva design page thumbnails as base64 data URIs.
    Returns {} if CANVA_ACCESS_TOKEN / CANVA_REFRESH_TOKEN not configured."""
    import requests
    token = _get_canva_token()
    if not token:
        print("[daily_brief] Canva not configured — using gradient placeholders for visuals")
        return {}
    try:
        resp = requests.get(
            f"https://api.canva.com/rest/v1/designs/{CANVA_DESIGN_ID}/pages",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 50},
            timeout=15,
        )
        resp.raise_for_status()
        page_map = {p["index"]: p["thumbnail"]["url"] for p in resp.json().get("items", [])}
        result = {}
        for num in set(page_nums):
            url = page_map.get(num)
            if not url:
                continue
            try:
                img = requests.get(url, timeout=20)
                if img.status_code == 200:
                    b64 = base64.b64encode(img.content).decode()
                    ct  = img.headers.get("Content-Type", "image/png").split(";")[0]
                    result[num] = f"data:{ct};base64,{b64}"
            except Exception:
                pass
        print(f"[daily_brief] Canva images: {len(result)}/{len(set(page_nums))} fetched")
        return result
    except Exception as e:
        print(f"[daily_brief] Canva API failed: {e}")
        return {}

# Five-email baseline — Claude updates this daily with live intel
FIVE_EMAIL_BASELINE = [
    {
        "num": 1, "send_date": "Tue May 26 · 10 AM GMT+7",
        "type": "Post-Sale Loyalty",
        "subject": "You got it. Here's how to use it.",
        "preview": "The ritual for everything you just ordered.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "lifestyle",
    },
    {
        "num": 2, "send_date": "Thu May 28 · 10 AM GMT+7",
        "type": "Re-Engage Non-Buyers",
        "subject": "the sale is gone. the skin glow isn't.",
        "preview": "You don't need a discount to start your ritual.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "scrub_duo",
    },
    {
        "num": 3, "send_date": "Sun Jun 1 · 10 AM GMT+7",
        "type": "Aloe Duo Education",
        "subject": "what aloe vera does at 2am",
        "preview": "(while you sleep, it's working.)",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "aloe_duo",
    },
    {
        "num": 4, "send_date": "Thu Jun 5 · 10 AM GMT+7",
        "type": "Father's Day Gift Push",
        "subject": "the gift for the man who says he doesn't want anything",
        "preview": "He does. You know he does.",
        "from_email": "hi@cobasdaughter.com",
        "canva_page": "gift_bundle",
    },
    {
        "num": 5, "send_date": "Tue Jun 10 · 10 AM GMT+7",
        "type": "Summer Body Prep",
        "subject": "summer bodies are made in June",
        "preview": "The 5-minute ritual. No gym required.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "scrub_duo",
    },
]

# ─── KLAVIYO CONTEXT ─────────────────────────────────────────────────────────

def get_klaviyo_context() -> str:
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
        result    = r.json()
        campaigns = result.get("data", [])
        included  = {i["id"]: i for i in result.get("included", [])}
        lines = []
        for c in campaigns:
            a       = c.get("attributes", {})
            msg_ids = [m["id"] for m in c.get("relationships", {}).get("campaign-messages", {}).get("data", [])]
            subjects = [
                included[mid].get("attributes", {}).get("definition", {}).get("content", {}).get("subject", "")
                for mid in msg_ids if mid in included
            ]
            subj = subjects[0] if subjects else "(no subject)"
            dt   = (a.get("send_time") or a.get("scheduled_at") or "")[:10]
            lines.append(f"  [{a.get('status','?')}] {dt} — \"{subj}\" ({a.get('name','?')})")
        return "Recent Klaviyo campaigns:\n" + "\n".join(lines) if lines else "No campaigns found."
    except Exception as e:
        return f"Klaviyo fetch failed: {e}"

# ─── GMAIL HELPERS ────────────────────────────────────────────────────────────

def build_gmail_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    token_json = os.environ.get("GMAIL_TOKEN_JSON")
    if not token_json:
        raise ValueError("GMAIL_TOKEN_JSON not set")
    token_data = json.loads(base64.b64decode(token_json))
    creds = Credentials.from_authorized_user_info(token_data)
    return build("gmail", "v1", credentials=creds)


def get_recent_brand_emails(service, hours_back: int = 48) -> dict:
    """Scan brand inbox for last 48h — daily real-time competitor tracking."""
    results     = {}
    cutoff      = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    after_epoch = int(cutoff.timestamp())
    for brand in REFERENCE_BRANDS:
        query = f"({brand['query']}) after:{after_epoch}"
        try:
            resp = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
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
        brand_data_text += f"\n{brand_name}:\n"
        if not emails:
            brand_data_text += "  No emails in the last 5 days.\n"
            continue
        for e in emails:
            if "error" in e:
                brand_data_text += f"  Error: {e['error']}\n"
            else:
                brand_data_text += f"  [{e['date'][:16]}] Subject: {e['subject']}\n  Snippet: {e['snippet']}\n  ---\n"

    baseline_text = ""
    for em in FIVE_EMAIL_BASELINE:
        baseline_text += f"  Email {em['num']}: {em['send_date']} — \"{em['subject']}\" ({em['type']})\n"

    prompt = f"""You are the email war room strategist for CoBa's Daughter — a Vietnamese DTC body care brand.

BRAND SNAPSHOT:
- Launched March 2026 · ~2,500 email subscribers · low open/click rates
- Products: Coffee Body Exfoliator (Scrub Duo) · Aloe Soothing Gel (Aloe Duo) · 3-in-1 Artisan Soap · Gift Bundle Sets
- Last campaign May 25: "Up to 27% OFF Sets & Bundles" · free shipping $50+
- Sender personas: ritual@cobasdaughter.com (founder/intimate) · hi@cobasdaughter.com (commercial)
- Voice: intimate · sensory · Vietnamese heritage · "low maintenance luxury"
- Hero copy: "The only coffee scrub with a green tea scent" · "99% pure aloe vera" · "3-in-1: hand wash / body wash / bubble bath"

KLAVIYO HISTORY:
{klaviyo_context}

COMPETITOR INBOX (last 48 hours — real-time):
{brand_data_text}

BASELINE 5-EMAIL PLAN:
{baseline_text}

CALENDAR: Today = {today} GMT+7 · Father's Day = June 15 · Summer peak = June-July

INSTRUCTIONS: Write a full Email War Room brief. Your response has exactly 6 parts.
- Part 1 is a Slack message. Parts 2-6 are email templates.
- Separate parts with ===EMAIL 1=== through ===EMAIL 5=== on their own lines.
- Do NOT echo these instructions. Do NOT add section labels, dashes, or headers.
- Start Part 1 immediately with the :red_circle: emoji line.

PART 1 FORMAT (Slack mrkdwn, under 2000 chars):
Write the Slack brief starting exactly like this (replace bracketed placeholders):

:red_circle: *CoBa's Daughter — Email War Room · {today}*
_Live Gmail scan · 48h real-time competitor intel · Klaviyo updated_

:inbox_tray: *WHAT YOUR INBOX SHOWS IN THE LAST 24H*
[1-sentence market mood based on competitor scan data — include specific subjects and offers if found]
• *Flamingo Estate* — [specific offer or "No emails this week"] · [N] sent · [started date or —]
• *Rhode* — [specific offer or "No emails this week"] · [N] sent · [started date or —]
• *OUAI* — [specific offer or "No emails this week"] · [N] sent · [started date or —]
• *Salt & Stone* — [specific offer or "No emails this week"] · [N] sent · [started date or —]
• *Nécessaire* — [specific offer or "No emails this week"] · [N] sent · [started date or —]
*Key pattern:* [1 sentence — dominant competitive theme right now]

:fire: *THE OPPORTUNITY RIGHT NOW*
[2-3 sentences: specific calendar white space · what nobody in body care is owning · CoBa's angle]

:white_check_mark: *YOUR 5-EMAIL PLAN — Updated {today}*
:e-mail: *Email 1 — [date · type label]*
> Subject: _"[subject line]"_
> Product: [name] · From: [persona name · email]
> Audience: [segment · Smart Send ON/OFF · exclude rule]
> UTM: `[slug]`
> CTA: _[button text]_
[Emails 2–5 same compact format]

:zap: *DO RIGHT NOW*
Step 1 → [exact Klaviyo menu path + action]
Step 2 → [...]
Step 3 → [...]

:bulb: *One steal:* [brand + specific tactic + why it applies to CoBa]

===EMAIL 1===
Subject: [exact subject line]
Preview text: [exact preview text]
From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
Segment: [exact segment description]

HERO IMAGE: [Specific visual: product name, styling, angle, lighting. E.g.: Scrub Duo jar on marble with scattered coffee grounds, warm morning light, overhead shot. Reference Canva design page if relevant.]

BODY:
[Full email copy, 160-200 words, CoBa brand voice. No "Dear"/"Hi". Open with 1 intimate sensory hook sentence. 2-3 short paragraphs: ingredient or ritual story + benefit + emotional resonance. Vietnamese heritage subtly if fitting. Gentle CTA close. Sign-off: — Méline OR — The CoBa's Daughter team]

PRODUCT IMAGE: [Secondary visual description, 300x300px OR NONE]

CTA BUTTON: [Button text, 2-5 words]

===EMAIL 2===
Subject: [exact subject line]
Preview text: [exact preview text]
From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
Segment: [exact segment description]

HERO IMAGE: [Specific visual description]

BODY:
[Full email copy, 160-200 words]

PRODUCT IMAGE: [Description OR NONE]

CTA BUTTON: [Button text]

===EMAIL 3===
Subject: [exact subject line]
Preview text: [exact preview text]
From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
Segment: [exact segment description]

HERO IMAGE: [Specific visual description]

BODY:
[Full email copy, 160-200 words]

PRODUCT IMAGE: [Description OR NONE]

CTA BUTTON: [Button text]

===EMAIL 4===
Subject: [exact subject line]
Preview text: [exact preview text]
From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
Segment: [exact segment description]

HERO IMAGE: [Specific visual description]

BODY:
[Full email copy, 160-200 words]

PRODUCT IMAGE: [Description OR NONE]

CTA BUTTON: [Button text]

===EMAIL 5===
Subject: [exact subject line]
Preview text: [exact preview text]
From name: [Méline at CoBa's Daughter OR CoBa's Daughter]
From email: [ritual@cobasdaughter.com OR hi@cobasdaughter.com]
Segment: [exact segment description]

HERO IMAGE: [Specific visual description]

BODY:
[Full email copy, 160-200 words]

PRODUCT IMAGE: [Description OR NONE]

CTA BUTTON: [Button text]"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

# ─── SLACK SENDER ─────────────────────────────────────────────────────────────

def post_to_slack(brief_text: str, today: str) -> str:
    from slack_sdk import WebClient
    token = os.environ.get("DAILY_BRIEF_SLACK_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("DAILY_BRIEF_SLACK_TOKEN or SLACK_BOT_TOKEN not set")
    client = WebClient(token=token)
    # Only send Slack section (before first ===EMAIL N===)
    slack_section = re.split(r"===EMAIL \d+===", brief_text)[0].strip()
    resp = client.chat_postMessage(channel=SLACK_USER_ID, text=slack_section, mrkdwn=True)
    return resp["ts"]

# ─── HTML RENDERING ───────────────────────────────────────────────────────────

SLACK_EMOJI_MAP = {
    ":red_circle:": "🔴", ":inbox_tray:": "📥", ":fire:": "🔥",
    ":white_check_mark:": "✅", ":e-mail:": "📧", ":zap:": "⚡",
    ":bulb:": "💡", ":warning:": "⚠️",
}


def _fmt_inline(text: str) -> str:
    """Apply bold, italic, code inline formatting."""
    text = re.sub(r"\*([^*]+)\*", r"<strong>\1</strong>", text)
    text = re.sub(r"_([^_]+)_",   r"<em>\1</em>",         text)
    text = re.sub(r"`([^`]+)`",
                  r"<code style='background:#f0ece4;padding:1px 5px;border-radius:3px;"
                  r"font-size:11px;font-family:monospace'>\1</code>", text)
    return text


def _render_md_table(table_lines: list, p: dict) -> str:
    """Convert | markdown table lines → styled HTML table."""
    rows = []
    for line in table_lines:
        stripped = line.strip().strip("|")
        if re.match(r"^[-| ]+$", stripped):
            continue  # separator row
        cells = [c.strip() for c in stripped.split("|")]
        rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    data   = rows[1:]
    thead = "".join(
        f"<th style='padding:8px 12px;text-align:left;color:#c9b99a;font-size:10px;"
        f"letter-spacing:1px;text-transform:uppercase;white-space:nowrap'>{h}</th>"
        for h in header
    )
    tbody = ""
    for i, row in enumerate(data):
        bg = p["white"] if i % 2 == 0 else p["cream"]
        cells = "".join(
            f"<td style='padding:8px 12px;font-size:12px;color:{p['dark_brown']};border-bottom:1px solid {p['border']}'>"
            f"{_fmt_inline(c)}</td>"
            for c in row
        )
        tbody += f"<tr style='background:{bg}'>{cells}</tr>"
    return (
        f"<div style='overflow-x:auto;margin:12px 0 16px'>"
        f"<table style='width:100%;border-collapse:collapse;background:{p['dark_brown']};border-radius:6px;overflow:hidden'>"
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{tbody}</tbody>"
        f"</table></div>"
    )


def _slack_to_html(text: str, p: dict) -> str:
    """Convert Slack mrkdwn to HTML, handling tables and emoji."""
    for code, emoji in SLACK_EMOJI_MAP.items():
        text = text.replace(code, emoji)

    lines  = text.split("\n")
    output = []
    i      = 0
    while i < len(lines):
        line = lines[i]
        # Detect markdown table block
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            output.append(_render_md_table(table_lines, p))
            continue
        # Escape HTML
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Blockquote rows (> ...)
        if safe.startswith("&gt; "):
            inner = _fmt_inline(safe[5:])
            output.append(
                f"<p style='margin:2px 0 2px 12px;color:{p['olive']};font-size:12px;"
                f"border-left:2px solid {p['rust']};padding-left:8px'>{inner}</p>"
            )
        # Step lines
        elif re.match(r"^Step \d", safe):
            output.append(f"<p style='margin:3px 0;font-size:12px;color:{p['dark_brown']}'>{_fmt_inline(safe)}</p>")
        # Emoji-prefixed section headers
        elif re.match(r"^[🔴📥🔥✅📧⚡💡⚠️]", safe):
            output.append(f"<p style='margin:20px 0 6px;font-size:14px;line-height:1.4'>{_fmt_inline(safe)}</p>")
        # Empty
        elif not safe.strip():
            output.append("<div style='height:6px'></div>")
        else:
            output.append(f"<p style='margin:4px 0;color:{p['dark_brown']};font-size:13px;line-height:1.6'>{_fmt_inline(safe)}</p>")
        i += 1
    return "\n".join(output)


def _parse_email_template(section_text: str) -> dict:
    """Parse an ===EMAIL N=== section into a structured dict using regex."""
    txt = section_text.strip()

    def field(pattern, default=""):
        m = re.search(pattern, txt, re.MULTILINE | re.IGNORECASE)
        return m.group(1).strip() if m else default

    result = {
        "subject":       field(r"^\**Subject:\**\s*[\"']?(.*?)[\"']?\s*$"),
        "preview":       field(r"^\**Preview text:\**\s*[\"']?(.*?)[\"']?\s*$"),
        "from_name":     field(r"^\**From name:\**\s*(.+)$"),
        "from_email":    field(r"^\**From email:\**\s*(.+)$"),
        "segment":       field(r"^\**Segment:\**\s*(.+)$"),
        "product_image": field(r"^\**PRODUCT IMAGE:\**\s*(.+)$"),
        "cta":           field(r"^\**CTA BUTTON:\**\s*(.+)$"),
        "hero_image":    "",
        "body":          "",
    }

    # Hero image: grab everything from HERO IMAGE: up to next blank line or BODY:
    hero_m = re.search(
        r"^\**HERO IMAGE:\**\s*\n?(.*?)(?=\n\s*\n|\nBODY:)",
        txt, re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    if not hero_m:
        hero_m = re.search(r"^\**HERO IMAGE:\**\s*(.+)$", txt, re.MULTILINE | re.IGNORECASE)
    if hero_m:
        result["hero_image"] = re.sub(r"\s+", " ", hero_m.group(1)).strip()

    # Body: everything between BODY: and PRODUCT IMAGE: or CTA BUTTON:
    body_m = re.search(
        r"^\**BODY:\**\s*\n(.*?)(?=\n\s*\n*\**PRODUCT IMAGE:|\n\s*\n*\**CTA BUTTON:)",
        txt, re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    if body_m:
        result["body"] = body_m.group(1).strip()

    return result


def _render_email_card(tpl: dict, num: int, p: dict) -> str:
    """Render one parsed email template as a complete HTML email mockup card."""
    # Metadata strip
    meta_rows = ""
    for label, val in [
        ("Subject",      tpl["subject"]),
        ("Preview",      tpl["preview"]),
        ("From",         f"{tpl['from_name']} &lt;{tpl['from_email']}&gt;"),
        ("To / Segment", tpl["segment"]),
    ]:
        if val:
            meta_rows += (
                f"<tr>"
                f"<td style='padding:3px 14px 3px 0;color:{p['light_text']};font-size:10px;"
                f"font-weight:700;letter-spacing:.5px;text-transform:uppercase;white-space:nowrap;vertical-align:top'>{label}</td>"
                f"<td style='padding:3px 0;color:{p['dark_brown']};font-size:12px'>{val}</td>"
                f"</tr>"
            )

    # Visual brief block — descriptive placeholder for the Canva image
    hero_desc = tpl.get("hero_image", "") or "Product lifestyle shot"
    hero_block = (
        f"<div style='width:100%;background:{p['beige']};border:2px dashed {p['border']};"
        f"border-radius:6px;margin-bottom:20px;padding:20px 24px;box-sizing:border-box'>"
        f"<div style='font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;"
        f"color:{p['rust']};margin-bottom:8px'>📸 Visual Block — Use from Canva design</div>"
        f"<div style='font-size:13px;color:{p['dark_brown']};line-height:1.7;font-style:italic'>"
        f"{hero_desc}"
        f"</div>"
        f"<div style='font-size:10px;color:{p['light_text']};margin-top:8px'>"
        f"600 × 300 px · hero image · upload to Klaviyo before sending"
        f"</div>"
        f"</div>"
    )

    # Body copy
    body_html = ""
    for para in tpl["body"].split("\n\n"):
        para = para.strip()
        if para:
            body_html += (
                f"<p style='margin:0 0 16px;line-height:1.8;font-size:13px;"
                f"color:{p['dark_brown']};font-family:Georgia,serif'>{para}</p>"
            )

    # Product image block
    prod_block = ""
    if tpl["product_image"] and tpl["product_image"].upper() not in ("NONE", ""):
        prod_block = (
            f"<div style='width:200px;height:200px;background:{p['beige']};border:1px solid {p['border']};"
            f"border-radius:4px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;"
            f"text-align:center;padding:12px;box-sizing:border-box'>"
            f"<div>"
            f"<div style='font-size:20px;margin-bottom:6px'>🖼</div>"
            f"<div style='color:{p['light_text']};font-size:10px;line-height:1.5;font-style:italic'>"
            f"{tpl['product_image']}"
            f"</div>"
            f"<div style='color:{p['light_text']};font-size:9px;margin-top:4px'>300 × 300 px</div>"
            f"</div>"
            f"</div>"
        )

    # CTA button
    cta_label = tpl["cta"] or "Shop Now →"
    cta_block = (
        f"<div style='text-align:center;margin:8px 0 24px'>"
        f"<span style='display:inline-block;background:{p['dark_brown']};color:#fff;"
        f"padding:13px 32px;border-radius:3px;font-size:13px;font-weight:600;letter-spacing:.5px'>"
        f"{cta_label}"
        f"</span>"
        f"</div>"
    )

    return (
        f"<div style='margin-bottom:32px'>"
        # Card header
        f"<div style='background:{p['dark_brown']};padding:10px 20px;border-radius:6px 6px 0 0'>"
        f"<span style='color:#c9b99a;font-size:10px;letter-spacing:2px;text-transform:uppercase;font-weight:700'>"
        f"✦ Email {num} — {tpl.get('from_name','').replace('CoBa','CoBa') or 'Campaign Template'}"
        f"</span>"
        f"</div>"
        # Metadata
        f"<div style='background:{p['beige']};padding:12px 20px;border-left:1px solid {p['border']};border-right:1px solid {p['border']}'>"
        f"<table style='font-family:\"Segoe UI\",Arial,sans-serif'><tbody>{meta_rows}</tbody></table>"
        f"</div>"
        # Email body mockup
        f"<div style='background:{p['white']};padding:24px 28px;border:1px solid {p['border']};border-top:none;border-radius:0 0 6px 6px'>"
        f"{hero_block}"
        f"{body_html}"
        f"{prod_block}"
        f"{cta_block}"
        f"</div>"
        f"</div>"
    )


def _render_html(brief_text: str, today: str) -> str:
    p = BRAND_PALETTE

    # Split into Slack section + 5 email template sections
    parts       = re.split(r"===EMAIL (\d+)===", brief_text)
    slack_text  = parts[0].strip()
    email_cards = ""

    # parts = [slack, "1", template1, "2", template2, ..., "5", template5]
    for idx in range(1, len(parts) - 1, 2):
        num     = int(parts[idx])
        content = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
        tpl     = _parse_email_template(content)
        email_cards += _render_email_card(tpl, num, p)

    brief_html = _slack_to_html(slack_text, p)

    # Priority checklist
    items = [
        ("🔴", "Set up <strong>ICYMI resend</strong> — 48h after each campaign to non-openers, different subject"),
        ("🔴", "Fill <strong>all preview texts</strong> — check every scheduled Klaviyo draft now"),
        ("🔴", "Add <strong>5–10% off trigger</strong> to Abandon Cart Email 2 (steal from Nécessaire)"),
        ("🟡", "Switch FROM name to <strong>\"Méline at CoBa's Daughter\"</strong> on brand emails"),
        ("🟡", "Create <strong>Engaged 90-day</strong> + <strong>At-Risk 90–180-day</strong> Klaviyo segments"),
        ("🟡", "Set up <strong>Post-Purchase Review Request</strong> flow (14 days after delivery)"),
        ("🟢", "Build <strong>Browse Abandonment</strong> flow (viewed product, no cart add)"),
        ("🟢", "Build <strong>Sunset / Winback</strong> flow for 180+ day non-openers"),
        ("🟢", "Enable <strong>A/B subject line test</strong> on every future campaign"),
    ]
    checklist_rows = "".join(
        f"<tr><td style='padding:4px 8px 4px 0;font-size:14px;vertical-align:top'>{icon}</td>"
        f"<td style='padding:4px 0;font-size:12px;color:{p['dark_brown']};line-height:1.5'>{text}</td></tr>"
        for icon, text in items
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{p['beige']};font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:720px;margin:24px auto 0;border-radius:8px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,.1)">

  <!-- HEADER -->
  <div style="background:{p['dark_brown']};padding:28px 36px">
    <div style="color:#c9b99a;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px">CoBa's Daughter</div>
    <div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:-.3px">Daily Email Marketing Update</div>
    <div style="color:rgba(255,255,255,.45);font-size:12px;margin-top:5px">{today} · 9:00 AM GMT+7 · Email War Room · Auto-generated</div>
  </div>

  <!-- WAR ROOM BRIEF -->
  <div style="background:{p['white']};padding:32px 36px 24px">
    {brief_html}
  </div>

  <!-- EMAIL TEMPLATES HEADER -->
  <div style="background:{p['beige']};padding:24px 36px 8px">
    <div style="color:{p['rust']};font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase">
      ✦ This Week's 5 Email Templates — Full Copy + Visual Blocks
    </div>
    <p style="color:{p['light_text']};font-size:12px;margin:6px 0 0;line-height:1.5">
      Each template is ready to build in Klaviyo. Visual block descriptions are inside each card —
      pull the matching asset from your
      <a href="https://www.canva.com/design/{CANVA_DESIGN_ID}/" style="color:{p['rust']}">Canva design</a>
      before sending.
    </p>
  </div>

  <!-- EMAIL TEMPLATE CARDS -->
  <div style="background:{p['beige']};padding:8px 36px 32px">
    {email_cards}
  </div>

  <!-- PRIORITY CHECKLIST -->
  <div style="background:{p['cream']};padding:0 36px 28px">
    <div style="background:{p['white']};border-left:3px solid {p['rust']};padding:16px 20px;border-radius:0 6px 6px 0">
      <div style="color:{p['rust']};font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">⚡ Ongoing Priority Checklist</div>
      <table style="width:100%"><tbody>{checklist_rows}</tbody></table>
    </div>
  </div>

  <!-- FOOTER -->
  <div style="background:{p['dark_brown']};padding:18px 36px;text-align:center">
    <div style="color:rgba(255,255,255,.35);font-size:11px">
      CoBa's Daughter · Daily Email Marketing Update · Auto-sent 9:02 AM GMT+7
    </div>
  </div>

</div>
</body></html>"""

# ─── EMAIL SENDER ─────────────────────────────────────────────────────────────

def send_email_brief(brief_text: str, today: str) -> None:
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD not set — see GMAIL_APP_PASSWORD_SETUP.md")

    html_body = _render_html(brief_text, today)
    # Plain-text: just the Slack section
    plain   = re.split(r"===EMAIL \d+===", brief_text)[0].strip()
    subject = f"CoBa's Daughter Daily Email Marketing Update — {today}"

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
        print(f"[daily_brief] {found} brand emails fetched (last 5 days)")
    except Exception as e:
        print(f"[daily_brief] Gmail fetch failed: {e}")

    # 2. Klaviyo context (optional)
    try:
        klaviyo_context = get_klaviyo_context()
        print(f"[daily_brief] Klaviyo: {len(klaviyo_context)} chars")
    except Exception as e:
        klaviyo_context = f"Klaviyo unavailable: {e}"

    # 3. Generate brief + 5 email templates
    print("[daily_brief] Generating War Room brief + 5 email templates…")
    try:
        brief = generate_brief(brand_emails, klaviyo_context, today)
        template_count = len(re.findall(r"===EMAIL \d+===", brief))
        print(f"[daily_brief] Brief ready ({len(brief)} chars, {template_count} email templates)")
    except Exception as e:
        print(f"[daily_brief] Claude failed: {e}")
        brief = (
            f":warning: *Daily brief failed today.*\n"
            f"Error: {e}\n\nCheck ANTHROPIC_API_KEY at console.anthropic.com"
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
