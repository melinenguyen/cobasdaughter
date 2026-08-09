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
import sys
import json
import base64
import datetime
import smtplib
import imaplib
import email as emaillib
from email.header import decode_header as _hdr_decode
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── CONFIG ──────────────────────────────────────────────────────────────────

REFERENCE_BRANDS = [
    # imap_terms: substrings searched inside the From header (display name + email address).
    # List most specific term first. IMAP FROM search is case-insensitive substring match.
    {"name": "Flamingo Estate",     "imap_terms": ["flamingoestate", "Flamingo Estate"]},
    {"name": "Rhode",               "imap_terms": ["rhodeskin", "rhode.com"]},
    {"name": "OUAI",                "imap_terms": ["theouai", "ouai.com"]},
    {"name": "Salt & Stone",        "imap_terms": ["saltandstone"]},
    {"name": "Nécessaire",          "imap_terms": ["necessaire"]},
    {"name": "Frank Body",          "imap_terms": ["frankbody", "Frank Body"]},
    {"name": "Koala Eco",           "imap_terms": ["koalaeco", "Koala Eco"]},
    {"name": "Kopari",              "imap_terms": ["koparibeauty", "kopari.com"]},
    {"name": "Herbivore",           "imap_terms": ["herbivorebotanicals", "Herbivore Botanicals"]},
    {"name": "Golde",               "imap_terms": ["golde.co", "hello@golde"]},
    {"name": "Youth To The People", "imap_terms": ["yttpbeauty", "yttp.com"]},
    {"name": "Osea",                "imap_terms": ["oseamalibu", "osea.com"]},
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

# ─── CAMPAIGN CALENDAR (self-updating) ────────────────────────────────────────
# Everything below is computed against the run date, so the brief never plans
# against a dead calendar. Before this existed the prompt was frozen at
# "Father's Day = June 15 · Summer peak = June-July" and kept saying so in August.

# Dated campaigns. Each auto-drops from the prompt once `end` passes — when the
# list empties the brief says so out loud rather than quietly planning on nothing.
ACTIVE_CAMPAIGNS = [
    {
        "name":  "CoBa's Endless Summer",
        "start": (2026, 6, 25),
        "end":   (2026, 9, 15),
        "hook":  "Keep your summer skin endlessly glowing",
        "focus": "Refillable ritual — Aloe Gel refill is the first-ever and the hero novelty. "
                 "Goal is repeat-refill behaviour for LTV plus clearing jar stock before Q4.",
        "skus":  "Coffee Set $88 · Aloe Set $69 · Coffee Refill 20oz $59 · Aloe Refill 20oz $46",
    },
]

# The strategic frame by month — never expires, so there is always an anchor even
# when no dated campaign is live. Keyed by month number.
SEASONAL_FRAME = {
    1: "New year reset · post-holiday skin recovery",
    2: "Valentine's gifting · self-ritual angle",
    3: "Spring renewal · brand anniversary (launched March 2026)",
    4: "Spring skin prep · Mother's Day warm-up",
    5: "Mother's Day peak · gifting sets",
    6: "Summer peak begins · Aloe hero · refill launch",
    7: "Summer peak · refill behaviour · travel sizes",
    8: "Late summer · after-sun recovery · refill repeat",
    9: "After-summer / back-to-school · transition to gifting",
    10: "Q4 gifting runway opens · bundle building",
    11: "Black Friday / Cyber Monday · biggest revenue window",
    12: "Thoughtful gifting · holiday close · new-year teaser",
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime.date:
    """Date of the nth `weekday` (Mon=0) in a month. Used for floating holidays."""
    d = datetime.date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + datetime.timedelta(days=offset + 7 * (n - 1))


def _holidays_for(year: int) -> list:
    """(date, label) for the retail dates worth planning email around."""
    thanksgiving = _nth_weekday(year, 11, 3, 4)  # 4th Thursday
    return [
        (datetime.date(year, 2, 14),      "Valentine's Day"),
        (_nth_weekday(year, 5, 6, 2),     "Mother's Day"),
        (_nth_weekday(year, 6, 6, 3),     "Father's Day"),
        (datetime.date(year, 7, 4),       "July 4th"),
        (datetime.date(year, 9, 1),       "Back-to-school window opens"),
        (thanksgiving,                    "Thanksgiving"),
        (thanksgiving + datetime.timedelta(days=1), "Black Friday"),
        (thanksgiving + datetime.timedelta(days=4), "Cyber Monday"),
        (datetime.date(year, 12, 25),     "Christmas"),
    ]


def build_calendar_context(today_date: datetime.date) -> str:
    """The CALENDAR block of the prompt, computed fresh every run."""
    lines = [f"Today = {today_date:%A, %B %-d, %Y} (GMT+7)",
             f"Season = {SEASONAL_FRAME[today_date.month]}"]

    live = []
    for c in ACTIVE_CAMPAIGNS:
        start = datetime.date(*c["start"])
        end   = datetime.date(*c["end"])
        if start <= today_date <= end:
            elapsed = (today_date - start).days
            total   = (end - start).days
            live.append(
                f"LIVE CAMPAIGN: {c['name']} — \"{c['hook']}\"\n"
                f"  Day {elapsed} of {total} · {(end - today_date).days} days left (ends {end:%b %-d})\n"
                f"  {c['focus']}\n"
                f"  SKUs: {c['skus']}"
            )
        elif today_date < start:
            live.append(
                f"UPCOMING CAMPAIGN: {c['name']} starts {start:%b %-d} "
                f"({(start - today_date).days} days out) — \"{c['hook']}\""
            )
    if live:
        lines += live
    else:
        lines.append(
            "NO DATED CAMPAIGN IS LIVE — plan against the seasonal frame above and say "
            "plainly in the brief that the campaign calendar needs the next window added."
        )

    # Next four retail dates, rolling into next year near the boundary
    upcoming = [(d, n) for d, n in _holidays_for(today_date.year) if d >= today_date]
    upcoming += [(d, n) for d, n in _holidays_for(today_date.year + 1)]
    nxt = sorted(upcoming)[:4]
    lines.append("Upcoming: " + " · ".join(
        f"{n} {d:%b %-d} ({(d - today_date).days}d)" for d, n in nxt
    ))
    return "\n".join(lines)


def build_send_schedule(today_date: datetime.date, count: int = 5) -> list:
    """Next `count` send slots — every 3rd day starting tomorrow, 10 AM GMT+7."""
    return [
        f"{today_date + datetime.timedelta(days=1 + 3 * i):%a %b %-d} · 10 AM GMT+7"
        for i in range(count)
    ]


# Five-email baseline — themes and personas only. Send dates are computed at run
# time by build_send_schedule(); they used to be hardcoded to May/June 2026.
FIVE_EMAIL_BASELINE = [
    {
        "num": 1,
        "type": "Refill Education — the first-ever Aloe refill",
        "subject": "the jar stays. the ritual refills.",
        "preview": "Your Aloe Gel now comes in a refill.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "aloe_duo",
    },
    {
        "num": 2,
        "type": "Replenishment — repeat-refill behaviour",
        "subject": "running low?",
        "preview": "About six weeks in, the jar starts to echo.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "ritual",
    },
    {
        "num": 3,
        "type": "Aloe Education — after-sun recovery",
        "subject": "what aloe vera does at 2am",
        "preview": "(while you sleep, it's working.)",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "aloe_duo",
    },
    {
        "num": 4,
        "type": "Scrub Duo conversion — the anchor SKU",
        "subject": "the only coffee scrub that smells like green tea",
        "preview": "Five minutes. Then the rest of your day.",
        "from_email": "ritual@cobasdaughter.com",
        "canva_page": "scrub_duo",
    },
    {
        "num": 5,
        "type": "Re-Engage Non-Buyers",
        "subject": "the sale is gone. the skin glow isn't.",
        "preview": "You don't need a discount to start your ritual.",
        "from_email": "hi@cobasdaughter.com",
        "canva_page": "lifestyle",
    },
]

# ─── KLAVIYO CONTEXT ─────────────────────────────────────────────────────────

# The Klaviyo key must point at CoBa's Daughter. Lixibox runs several brands in
# separate Klaviyo accounts (Halio Sonic among them), and a key for the wrong one
# still returns 200 — it just feeds another brand's campaign history into the
# brief. Checked on every run rather than trusted.
KLAVIYO_EXPECTED_ORG = "coba"


def _klaviyo_account_name(headers: dict) -> str:
    """Organization name on the account the API key belongs to ('' if unavailable)."""
    import requests
    try:
        r = requests.get("https://a.klaviyo.com/api/accounts/", headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return ""
        return (data[0].get("attributes", {})
                       .get("contact_information", {})
                       .get("organization_name", ""))
    except Exception as e:
        print(f"[daily_brief] Klaviyo account lookup failed: {e}")
        return ""


def get_klaviyo_context() -> str:
    api_key = os.environ.get("KLAVIYO_PRIVATE_API_KEY")
    if not api_key:
        return "Klaviyo not connected (KLAVIYO_PRIVATE_API_KEY not set)."
    import requests
    try:
        h = {"Authorization": f"Klaviyo-API-Key {api_key}", "revision": "2024-02-15"}

        org = _klaviyo_account_name(h)
        print(f"[daily_brief] Klaviyo account: {org or 'unknown'}")
        header = f"Klaviyo account: {org}\n" if org else ""
        if org and KLAVIYO_EXPECTED_ORG not in org.lower():
            header = (
                f"⚠️ WRONG KLAVIYO ACCOUNT — this key belongs to \"{org}\", not CoBa's Daughter. "
                f"The campaign history below is another brand's. Ignore it when planning, and "
                f"say so at the top of the brief.\n"
            )

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
        if not lines:
            return header + "No campaigns found."
        return header + "Recent campaigns (most recent first):\n" + "\n".join(lines)
    except Exception as e:
        return f"Klaviyo fetch failed: {e}"

# ─── GMAIL HELPERS (IMAP — uses GMAIL_APP_PASSWORD, no OAuth needed) ──────────

def _imap_decode(value: str) -> str:
    """Decode encoded email header value (handles UTF-8, ISO-8859, etc.)."""
    if not value:
        return ""
    parts = []
    for chunk, enc in _hdr_decode(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return " ".join(parts)


def build_imap_connection():
    """Connect to Gmail via IMAP using GMAIL_APP_PASSWORD — same password used for sending."""
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise ValueError("GMAIL_APP_PASSWORD not set")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(EMAIL_TO, password)
    print(f"[daily_brief] IMAP connected as: {EMAIL_TO}")
    return mail


def _imap_fetch_emails(mail, search_term: str, since_str: str) -> list:
    """Search [Gmail]/All Mail for emails FROM a term since a date."""
    results = []
    try:
        # IMAP FROM search is a substring match against the full From header
        status, data = mail.search(None, f'FROM "{search_term}" SINCE "{since_str}"')
        if status != "OK" or not data[0]:
            return []
        nums = data[0].split()[-15:]  # up to 15 most recent
        for num in nums:
            _, msg_data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
            msg = emaillib.message_from_bytes(raw)
            results.append({
                "subject": _imap_decode(msg.get("Subject", "(no subject)")),
                "from":    _imap_decode(msg.get("From", "")),
                "date":    msg.get("Date", ""),
                "snippet": "",
            })
    except Exception as e:
        print(f"[daily_brief]   IMAP search '{search_term}': {e}")
    return results


def get_recent_brand_emails(mail, days_back: int = 5) -> dict:
    """Scan Gmail via IMAP for all reference brands over the last 5 days."""
    cutoff    = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    since_str = cutoff.strftime("%d-%b-%Y")  # e.g. "22-May-2026"

    # Select All Mail so we search every folder (inbox, promotions, social, etc.)
    status, _ = mail.select('"[Gmail]/All Mail"', readonly=True)
    if status != "OK":
        mail.select("INBOX", readonly=True)

    results = {}
    for brand in REFERENCE_BRANDS:
        seen_ids = set()
        brand_emails = []
        for term in brand["imap_terms"]:
            for em in _imap_fetch_emails(mail, term, since_str):
                key = (em["date"], em["subject"])
                if key not in seen_ids:
                    seen_ids.add(key)
                    brand_emails.append(em)
        results[brand["name"]] = brand_emails
        print(f"[daily_brief]   {brand['name']}: {len(brand_emails)} emails")
    return results


def get_all_promo_senders(mail, days_back: int = 5) -> list:
    """Scan ALL marketing emails from last 5 days — catches every brand not in reference list.

    Searches Gmail's Promotions folder, then checks for List-Unsubscribe header
    (present in all legitimate marketing email regardless of which tab it lands in).
    """
    cutoff    = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    since_str = cutoff.strftime("%d-%b-%Y")
    ref_names = {b["name"].lower() for b in REFERENCE_BRANDS}

    # Try Promotions folder first, fall back to All Mail
    folder_selected = None
    for folder in ['"[Gmail]/Promotions"', '"Promotions"', '"[Gmail]/All Mail"']:
        try:
            status, _ = mail.select(folder, readonly=True)
            if status == "OK":
                folder_selected = folder
                print(f"[daily_brief] Promo scan folder: {folder}")
                break
        except Exception:
            continue

    if not folder_selected:
        return []

    senders, seen = [], set()
    try:
        _, nums = mail.search(None, f'SINCE "{since_str}"')
        for num in (nums[0].split() or [])[-100:]:
            _, msg_data = mail.fetch(
                num,
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT LIST-UNSUBSCRIBE)])"
            )
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
            msg      = emaillib.message_from_bytes(raw)
            from_raw = _imap_decode(msg.get("From", ""))
            subject  = _imap_decode(msg.get("Subject", ""))
            has_unsub        = bool(msg.get("List-Unsubscribe"))
            already_tracked  = any(n in from_raw.lower() for n in ref_names)
            sender_key       = from_raw.lower()
            if has_unsub and not already_tracked and from_raw and sender_key not in seen:
                seen.add(sender_key)
                senders.append({"from": from_raw, "subject": subject, "snippet": ""})
    except Exception as e:
        print(f"[daily_brief] Promo scan error: {e}")

    print(f"[daily_brief] Full promo scan: {len(senders)} unique non-reference senders")
    return senders

# ─── BRIEF GENERATOR ─────────────────────────────────────────────────────────

def generate_brief(brand_emails: dict, klaviyo_context: str, today: str,
                   all_promos: list = None, today_date: datetime.date = None) -> str:
    from anthropic import Anthropic
    client = Anthropic()

    brand_data_text = ""
    for brand_name, emails in brand_emails.items():
        brand_data_text += f"\n{brand_name}:\n"
        if not emails:
            brand_data_text += "  No emails in the last 48h.\n"
            continue
        for e in emails:
            if "error" in e:
                brand_data_text += f"  Error: {e['error']}\n"
            else:
                brand_data_text += f"  [{e['date'][:16]}] Subject: {e['subject']}\n  Snippet: {e['snippet']}\n  ---\n"

    other_promos_text = ""
    if all_promos:
        for p in all_promos:
            other_promos_text += f"  From: {p['from']}\n  Subject: {p['subject']}\n  Preview: {p['snippet']}\n  ---\n"
    else:
        other_promos_text = "  No additional promotional emails found.\n"

    baseline_text = ""
    if today_date is None:
        today_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).date()
    calendar_context = build_calendar_context(today_date)

    schedule = build_send_schedule(today_date)
    for em, slot in zip(FIVE_EMAIL_BASELINE, schedule):
        baseline_text += f"  Email {em['num']}: {slot} — \"{em['subject']}\" ({em['type']})\n"

    prompt = f"""You are the email war room strategist for CoBa's Daughter — a Vietnamese DTC body care brand.

BRAND SNAPSHOT:
- Launched March 2026 · low open rate (~13%) is the standing problem to beat
- Positioning: "Low-maintenance luxury body care for the Disciplined Woman" · ritual = UNWIND · RESET · RECOVER
- Products: Coffee Body Exfoliator (Scrub Duo — the anchor SKU) · Aloe Soothing Gel (Aloe Duo) · 3-in-1 Artisan Soap · Gift Bundles · refills (Coffee 20oz, Aloe 20oz)
- Sender personas: ritual@cobasdaughter.com (founder/intimate) · hi@cobasdaughter.com (commercial)
- Voice: intimate · sensory · Vietnamese heritage · "low maintenance luxury"
- Hero copy: "The only coffee scrub with a green tea scent" · "99% pure aloe vera" · "3-in-1: hand wash / body wash / bubble bath"
- Origin audience: the equestrian circuit — they found the Coffee Scrub post-competition

KLAVIYO HISTORY:
{klaviyo_context}

REFERENCE BRAND INBOX (last 5 days — rolling window):
{brand_data_text}

FULL PROMOTIONAL INBOX SCAN (last 5 days — every other brand that emailed):
{other_promos_text}

BASELINE 5-EMAIL PLAN (themes to adapt — the send slots are already correct, use them as given):
{baseline_text}

CALENDAR:
{calendar_context}

INSTRUCTIONS: Write a full Email War Room brief. Your response has exactly 6 parts.
- Part 1 is a Slack message. Parts 2-6 are email templates.
- Separate parts with ===EMAIL 1=== through ===EMAIL 5=== on their own lines.
- Do NOT echo these instructions. Do NOT add section labels, dashes, or headers.
- Start Part 1 immediately with the :red_circle: emoji line.

PART 1 FORMAT (Slack mrkdwn, under 2000 chars):
Write the Slack brief starting exactly like this (replace bracketed placeholders):

:red_circle: *CoBa's Daughter — Email War Room · {today}*
_Live Gmail scan · 5-day rolling window · Klaviyo updated_

:inbox_tray: *WHAT YOUR INBOX SHOWS IN THE LAST 24H*
[1-sentence market mood — based on ALL brands that emailed today, not just reference brands]
[For every reference brand that sent an email, write one bullet. Skip brands with zero emails — do not write "No emails". Only report what actually sent.]
• *[Brand name]* — [specific offer or theme from subject/snippet] · [N] emails · [key subject line]
[After reference brands, add a compact block for any notable brands from the full promo scan:]
:mailbox: *Also in your inbox today:* [comma-separated list of other brand names that sent promotional emails — include all of them]
*Key pattern:* [1 sentence — dominant theme across everything that landed today]

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
    try:
        resp = client.chat_postMessage(channel=SLACK_USER_ID, text=slack_section, mrkdwn=True)
    except Exception as e:
        # Posting straight to a user ID normally works; if the bot has never opened
        # a DM it can return channel_not_found. Open the IM channel and retry.
        if "channel_not_found" not in str(e):
            raise
        print("[daily_brief] channel_not_found — opening IM channel and retrying")
        dm   = client.conversations_open(users=[SLACK_USER_ID])
        resp = client.chat_postMessage(
            channel=dm["channel"]["id"], text=slack_section, mrkdwn=True
        )
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
    vn_tz      = datetime.timezone(datetime.timedelta(hours=7))
    now_vn     = datetime.datetime.now(vn_tz)
    today      = now_vn.strftime("%A, %B %-d, %Y")
    today_date = now_vn.date()
    print(f"[daily_brief] Starting for {today}")

    # Every step below is caught so one broken integration can't stop the rest of the
    # run. Anything recorded here re-raises as a non-zero exit at the end, otherwise a
    # dead credential looks like a green run — that is how a 7-day Gmail outage in
    # August 2026 went unnoticed.
    failures = []

    # 1. Gmail inbox scan via IMAP (uses GMAIL_APP_PASSWORD — no OAuth token needed)
    brand_emails  = {b["name"]: [] for b in REFERENCE_BRANDS}
    all_promos    = []
    gmail_warning = ""
    try:
        mail         = build_imap_connection()
        brand_emails = get_recent_brand_emails(mail)
        all_promos   = get_all_promo_senders(mail)
        mail.logout()
        found = sum(len(v) for v in brand_emails.values())
        print(f"[daily_brief] {found} reference brand emails + {len(all_promos)} unique other promo senders (last 5 days)")
        if found == 0 and len(all_promos) == 0:
            gmail_warning = (
                "\n\n⚠️ *Gmail inbox scan returned 0 emails.* "
                "Make sure IMAP is enabled in Gmail settings: "
                "Gmail → Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP."
            )
            failures.append("Gmail scan returned 0 emails")
    except Exception as e:
        print(f"[daily_brief] Gmail IMAP failed: {e}")
        gmail_warning = f"\n\n⚠️ *Gmail scan failed:* `{e}`"
        failures.append(f"Gmail scan: {e}")

    # 2. Klaviyo context (optional)
    try:
        klaviyo_context = get_klaviyo_context()
        print(f"[daily_brief] Klaviyo: {len(klaviyo_context)} chars")
    except Exception as e:
        klaviyo_context = f"Klaviyo unavailable: {e}"

    # 3. Generate brief + 5 email templates
    print("[daily_brief] Generating War Room brief + 5 email templates…")
    try:
        brief = generate_brief(brand_emails, klaviyo_context, today, all_promos, today_date)
        if gmail_warning:
            # Prepend warning to Slack section (before first ===EMAIL===)
            brief = gmail_warning.strip() + "\n\n" + brief
        template_count = len(re.findall(r"===EMAIL \d+===", brief))
        print(f"[daily_brief] Brief ready ({len(brief)} chars, {template_count} email templates)")
    except Exception as e:
        print(f"[daily_brief] Claude failed: {e}")
        brief = (
            f":warning: *Daily brief failed today.*\n"
            f"Error: {e}\n\nCheck ANTHROPIC_API_KEY at console.anthropic.com"
        )
        failures.append(f"Claude generation: {e}")

    # 4. Slack DM
    print("[daily_brief] Posting to Slack…")
    try:
        ts = post_to_slack(brief, today)
        print(f"[daily_brief] Slack ts: {ts}")
    except Exception as e:
        print(f"[daily_brief] Slack failed: {e}")
        failures.append(f"Slack post: {e}")

    # 5. Email
    print(f"[daily_brief] Sending email to {EMAIL_TO} (cc {EMAIL_CC})…")
    try:
        send_email_brief(brief, today)
        print("[daily_brief] Email sent.")
    except Exception as e:
        print(f"[daily_brief] Email failed: {e}")
        failures.append(f"Email send: {e}")

    print("[daily_brief] Done.")

    if failures:
        print(f"\n[daily_brief] {len(failures)} step(s) failed:")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
