#!/usr/bin/env python3
"""
CoBa's Daughter — Daily Email Marketing Brief Generator
Runs daily at 9AM GMT+7 (2AM UTC).
Scans brand inboxes → generates plan → posts to Slack DM + sends email.

Environment vars / GitHub Secrets needed:
  ANTHROPIC_API_KEY    — Claude API key
  SLACK_BOT_TOKEN      — Slack bot token (xoxb-...)
  SLACK_USER_ID        — Méline's Slack user ID  (default: U08V8865GD7)
  GMAIL_TOKEN_JSON     — Gmail OAuth token JSON, base64-encoded
"""

import os
import json
import base64
import datetime
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── CONFIG ───────────────────────────────────────────────────────────────────

REFERENCE_BRANDS = [
    {"name": "Flamingo Estate",  "query": "from:flamingoestate.com newer_than:2d"},
    {"name": "Rhode",            "query": "from:rhodeskin.com newer_than:2d"},
    {"name": "OUAI",             "query": "from:theouai.com newer_than:2d"},
    {"name": "Salt & Stone",     "query": "from:saltandstone.com newer_than:2d"},
    {"name": "Nécessaire",       "query": "from:necessaire.com newer_than:2d"},
]

SLACK_USER_ID      = os.environ.get("SLACK_USER_ID", "U08V8865GD7")
EMAIL_TO           = "meline.nguyen@lixibox.com"
EMAIL_CC           = "phuonglt.job@gmail.com"

CASH_COW_PRODUCTS  = ["Scrub Duo", "Aloe Duo", "Gift Bundle", "3-in-1 Artisan Soap"]

BRAND_PALETTE = {
    "dark_brown": "#2a1f17",
    "rust":       "#6b4423",
    "olive":      "#716a56",
    "beige":      "#f5f1ea",
    "light_text": "#9b8b7a",
}

# ─── WEEK PLAN (static baseline, updated by Claude each day) ──────────────────

WEEKLY_PLAN = [
    {
        "week":   "Week of May 26",
        "emails": [
            {
                "send_date": "Tue May 27 · 10 AM GMT+7",
                "type":      "Product Education",
                "subject":   "one really good scrub",
                "preview":   "(and one to follow it up). your 2-step glow ritual, explained.",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "Scrub Duo deep-dive. Rhode 'one really good' format. No hard sell.",
                "cta":       "Shop The Scrub Duo — 27% off",
                "segment":   "All engaged (opens 90d). Exclude Scrub Duo purchasers 60d.",
                "smart_send":"ON",
            },
            {
                "send_date": "Thu May 29 · 10 AM GMT+7",
                "type":      "Social Proof + Bundle Push",
                "subject":   '"My skin has never felt this soft."',
                "preview":   "That's not us talking. 3 customers. 1 product.",
                "from_name": "CoBa's Daughter",
                "from_email":"hi@cobasdaughter.com",
                "angle":     "3 real reviews → bridge to 27% off sets. Salt & Stone UGC formula.",
                "cta":       "Shop Best-Loved Sets",
                "segment":   "Full engaged list. Exclude recent purchasers 30d.",
                "smart_send":"ON",
            },
            {
                "send_date": "Sun Jun 1 · 10 AM GMT+7",
                "type":      "Last-Chance Urgency Close",
                "subject":   "Last Chance ✨",
                "preview":   "27% off our sets ends tonight. Sunday ritual, unlocked.",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "One full-width lifestyle image. 3 product tiles. Bundle savings end tonight.",
                "cta":       "Shop Before It Ends",
                "segment":   "Non-purchasers + email clickers who didn't buy. Smart Send OFF.",
                "smart_send":"OFF — final push",
            },
        ],
    },
    {
        "week":   "Week of Jun 2",
        "emails": [
            {
                "send_date": "Tue Jun 3 · 10 AM GMT+7",
                "type":      "Ingredient Story",
                "subject":   "what aloe vera does at 2am",
                "preview":   "(while you sleep, it's working. here's how.)",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "Aloe Duo night-repair science angle. Flamingo Estate heritage storytelling.",
                "cta":       "Shop The Aloe Duo",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
            {
                "send_date": "Thu Jun 5 · 10 AM GMT+7",
                "type":      "Q&A / FAQ Education",
                "subject":   "the 3-in-1 soap question we always get",
                "preview":   '"Can I use it on my face?" Yes. Here\'s why.',
                "from_name": "CoBa's Daughter",
                "from_email":"hi@cobasdaughter.com",
                "angle":     "Rhode 'ask rhode' format. Top FAQ about 3-in-1 Soap. Show all 3 uses visually.",
                "cta":       "Shop The 3-in-1 Soap",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
            {
                "send_date": "Sat Jun 7 · 10 AM GMT+7",
                "type":      "Gift Bundle Self-Gift Angle",
                "subject":   "the gift that comes back around",
                "preview":   "Everyone else gets flowers. You get something that lasts.",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "Post-Mother's Day pivot: buy for yourself. Gift Bundle lifestyle shoot.",
                "cta":       "Shop The Gift Bundle",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
        ],
    },
    {
        "week":   "Week of Jun 9",
        "emails": [
            {
                "send_date": "Tue Jun 10 · 10 AM GMT+7",
                "type":      "Founder's Letter",
                "subject":   "a small letter from méline",
                "preview":   "why I started this with my mother's hands in mind.",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "Personal origin story. No hard sell. Flamingo Estate Friday letter format.",
                "cta":       "Explore our rituals →",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
            {
                "send_date": "Thu Jun 12 · 10 AM GMT+7",
                "type":      "Best-Seller Spotlight",
                "subject":   "the one we can't keep on shelves",
                "preview":   "(spoiler: it's the soap)",
                "from_name": "CoBa's Daughter",
                "from_email":"hi@cobasdaughter.com",
                "angle":     "Nécessaire-style minimalism. One hero image. 'SOLD OUT X TIMES.' One CTA.",
                "cta":       "Shop The 3-in-1 Soap",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
            {
                "send_date": "Sat Jun 14 · 10 AM GMT+7",
                "type":      "Ritual Guide / How-To",
                "subject":   "your 5-minute weekend ritual",
                "preview":   "No appointments. No complicated steps. Just this.",
                "from_name": "Méline at CoBa's Daughter",
                "from_email":"ritual@cobasdaughter.com",
                "angle":     "Rhode routine angle. Step-by-step using all 4 hero products.",
                "cta":       "Shop All 4 Products",
                "segment":   "Full engaged list.",
                "smart_send":"ON",
            },
        ],
    },
]

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


def get_recent_brand_emails(service, hours_back: int = 26) -> dict:
    results = {}
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    after_epoch = int(cutoff.timestamp())

    for brand in REFERENCE_BRANDS:
        query = f"({brand['query']}) after:{after_epoch}"
        try:
            resp = service.users().messages().list(
                userId="me", q=query, maxResults=5
            ).execute()
            msgs = resp.get("messages", [])
            brand_emails = []
            for ref in msgs:
                msg = service.users().messages().get(
                    userId="me",
                    messageId=ref["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                hdrs = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                brand_emails.append({
                    "subject": hdrs.get("Subject", "(no subject)"),
                    "from":    hdrs.get("From", ""),
                    "date":    hdrs.get("Date", ""),
                    "snippet": msg.get("snippet", "")[:200],
                })
            results[brand["name"]] = brand_emails
        except Exception as e:
            results[brand["name"]] = [{"error": str(e)}]

    return results

# ─── BRIEF GENERATOR ─────────────────────────────────────────────────────────

def generate_brief(brand_emails: dict, today: str) -> str:
    from anthropic import Anthropic

    client = Anthropic()

    brand_data_text = ""
    for brand_name, emails in brand_emails.items():
        brand_data_text += f"\n### {brand_name}\n"
        if not emails:
            brand_data_text += "  No emails in the last 24h.\n"
            continue
        for e in emails:
            if "error" in e:
                brand_data_text += f"  Error: {e['error']}\n"
            else:
                brand_data_text += (
                    f"  Subject: {e['subject']}\n"
                    f"  Snippet: {e['snippet']}\n"
                    f"  ---\n"
                )

    # Serialise the week-1 plan for reference
    week1 = WEEKLY_PLAN[0]
    plan_text = f"This week ({week1['week']}) plan:\n"
    for idx, em in enumerate(week1["emails"], 1):
        plan_text += (
            f"  Email {idx}: {em['send_date']} — "{em['subject']}" — {em['type']}\n"
        )

    prompt = textwrap.dedent(f"""
        You are the email marketing strategist for CoBa's Daughter — a clean beauty DTC brand
        launched March 2026, ~2,500 subscribers. Cash-cow products: {', '.join(CASH_COW_PRODUCTS)}.
        Brand voice: intimate, editorial, artisan. Goals: lift open rate + click rate (both poor).
        Send 3 campaigns/week.

        Today is {today} (Vietnam time, GMT+7).

        ──────────────────────────────────────────────
        BRAND EMAILS RECEIVED IN THE LAST 24 HOURS:
        {brand_data_text}
        ──────────────────────────────────────────────
        THIS WEEK'S 3-EMAIL PLAN:
        {plan_text}
        ──────────────────────────────────────────────

        Write a concise daily Slack brief with EXACTLY these sections (use Slack mrkdwn):

        *📬 Brand Intel — What They Sent Today*
        For each brand that sent an email: 1 sentence on their angle + 1 tactic to steal.
        (Skip brands with no emails today.)

        *📅 Today's CoBa Action*
        One concrete task: draft copy, set up a Klaviyo segment, write subject variants, etc.

        *⚡ 3 Quick Wins*
        Three things under 30 min that improve this week's campaign.

        *📊 Pipeline*
        Which of this week's 3 emails is next and when it sends. Flag if overdue.

        *✦ Subject Line of the Day*
        One high-converting subject for one of the 4 cash-cow products.
        Format: `subject line here` — _one-sentence reason why it works_

        Constraints: tight writing, no fluff, total under 1 800 chars.
    """).strip()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ─── SLACK SENDER ─────────────────────────────────────────────────────────────

def post_to_slack(brief_text: str, today: str) -> str:
    from slack_sdk import WebClient

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not set")

    client = WebClient(token=token)
    header = f"*📧 CoBa's Daughter — Daily Email Marketing Brief*\n_{today} · 9:00 AM GMT+7_\n\n"
    full   = header + brief_text
    resp   = client.chat_postMessage(
        channel=SLACK_USER_ID,
        text=full,
        mrkdwn=True,
    )
    return resp["ts"]


# ─── EMAIL SENDER ─────────────────────────────────────────────────────────────

def _render_html(brief_text: str, today: str) -> str:
    """Wrap the plain-text brief + the full 3-week plan into a branded HTML email."""
    p   = BRAND_PALETTE
    B   = p["dark_brown"]
    R   = p["rust"]
    OL  = p["olive"]
    BG  = p["beige"]
    LT  = p["light_text"]

    def md_to_html(text: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # headers
            if line.startswith("*") and line.endswith("*") and line.count("*") == 2:
                inner = line[1:-1]
                lines.append(f"<h3 style='color:{R};margin:20px 0 6px;font-size:14px;letter-spacing:.5px'>{inner}</h3>")
            # bold
            import re
            line = re.sub(r"\*([^*]+)\*", r"<strong>\1</strong>", line)
            line = re.sub(r"_([^_]+)_",   r"<em>\1</em>",         line)
            line = re.sub(r"`([^`]+)`",   r"<code style='background:#f0ece4;padding:1px 4px;border-radius:3px'>\1</code>", line)
            if line.strip() == "":
                lines.append("<br>")
            else:
                lines.append(f"<p style='margin:4px 0;color:{B}'>{line}</p>")
        return "\n".join(lines)

    brief_html = md_to_html(brief_text)

    # Build plan table rows
    plan_rows = ""
    for week_block in WEEKLY_PLAN:
        for em in week_block["emails"]:
            plan_rows += f"""
            <tr style='border-bottom:1px solid #ece8e0'>
              <td style='padding:10px 12px;font-size:12px;color:{LT};white-space:nowrap'>{em['send_date']}</td>
              <td style='padding:10px 12px;font-size:12px;font-weight:700;color:{R}'>{em['type']}</td>
              <td style='padding:10px 12px;font-size:12px;color:{B}'><code style='background:#f0ece4;padding:2px 6px;border-radius:3px'>{em['subject']}</code></td>
              <td style='padding:10px 12px;font-size:12px;color:{OL}'>{em['from_email']}</td>
              <td style='padding:10px 12px;font-size:12px;color:{B}'>{em['angle'][:80]}…</td>
              <td style='padding:10px 12px;font-size:12px;font-weight:700;color:{B}'>{em['cta']}</td>
              <td style='padding:10px 12px;font-size:11px;color:{LT}'>{em['smart_send']}</td>
            </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{BG};font-family:'Segoe UI',Arial,sans-serif">
  <div style="max-width:700px;margin:24px auto 0;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">

    <!-- HEADER -->
    <div style="background:{B};padding:28px 36px">
      <div style="color:#c9b99a;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px">CoBa's Daughter</div>
      <div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:-.3px">Daily Email Marketing Brief</div>
      <div style="color:rgba(255,255,255,.5);font-size:12px;margin-top:4px">{today} · 9:00 AM GMT+7 · Auto-generated</div>
    </div>

    <!-- BRIEF BODY -->
    <div style="background:#fff;padding:32px 36px">
      {brief_html}
    </div>

    <!-- DIVIDER -->
    <div style="background:{BG};padding:24px 36px 0">
      <div style="color:{R};font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:16px">
        ✦ Auto-Updating 3-Email Weekly Plan
      </div>
    </div>

    <!-- PLAN TABLE -->
    <div style="background:{BG};padding:0 12px 24px;overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif">
        <thead>
          <tr style="background:{B}">
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase;white-space:nowrap">Send Date</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">Type</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">Subject Line</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">Sender</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">Angle</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">CTA</th>
            <th style="padding:10px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px;text-transform:uppercase">Smart Send</th>
          </tr>
        </thead>
        <tbody>
          {plan_rows}
        </tbody>
      </table>
    </div>

    <!-- QUICK-WIN CHECKLIST -->
    <div style="background:{BG};padding:0 36px 28px">
      <div style="background:#fff;border-left:3px solid {R};padding:16px 20px;border-radius:0 6px 6px 0">
        <div style="color:{R};font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">⚡ Immediate Priority Checklist</div>
        <table style="width:100%;font-size:12px;color:{B}">
          <tr><td style="padding:4px 0">🔴&nbsp;</td><td>Add <strong>5–10% off trigger</strong> to Abandon Cart Email 2 (steal from Nécessaire's $10 off)</td></tr>
          <tr><td style="padding:4px 0">🔴&nbsp;</td><td>Set up <strong>ICYMI resend</strong> — 48h after each campaign, different subject, to non-openers</td></tr>
          <tr><td style="padding:4px 0">🔴&nbsp;</td><td>Fill <strong>all preview texts</strong> — check every scheduled draft right now</td></tr>
          <tr><td style="padding:4px 0">🟡&nbsp;</td><td>Switch FROM name to <strong>"Méline at CoBa's Daughter"</strong> on brand/story emails</td></tr>
          <tr><td style="padding:4px 0">🟡&nbsp;</td><td>Create <strong>Engaged 90-day segment</strong> + <strong>At-Risk 90–180-day segment</strong> in Klaviyo</td></tr>
          <tr><td style="padding:4px 0">🟡&nbsp;</td><td>Set up <strong>Post-Purchase Review Request</strong> flow (14 days after delivery)</td></tr>
          <tr><td style="padding:4px 0">🟢&nbsp;</td><td>Build <strong>Browse Abandonment</strong> flow (viewed product, no add-to-cart)</td></tr>
          <tr><td style="padding:4px 0">🟢&nbsp;</td><td>Build <strong>Sunset/Winback</strong> flow for 180+ day non-openers</td></tr>
          <tr><td style="padding:4px 0">🟢&nbsp;</td><td>Enable <strong>A/B subject line split</strong> on every future campaign</td></tr>
        </table>
      </div>
    </div>

    <!-- BRAND INTEL SNAPSHOT -->
    <div style="background:{BG};padding:0 36px 28px">
      <div style="color:{R};font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px">📬 Brand Strategy Cheat-Sheet</div>
      <table style="width:100%;font-size:12px;border-collapse:collapse">
        <tr style="background:{B}">
          <th style="padding:8px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px">Brand</th>
          <th style="padding:8px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px">Freq</th>
          <th style="padding:8px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px">Top Tactic to Steal</th>
          <th style="padding:8px 12px;text-align:left;color:#c9b99a;font-size:10px;letter-spacing:1px">Subject Line Style</th>
        </tr>
        <tr style="background:#fff;border-bottom:1px solid {BG}">
          <td style="padding:8px 12px;font-weight:700;color:{B}">Flamingo Estate</td>
          <td style="padding:8px 12px;color:{LT}">2×/day</td>
          <td style="padding:8px 12px;color:{B}">Dual persona: founder essay (Fri) + product concierge. Award-credibility subject lines.</td>
          <td style="padding:8px 12px;color:{OL}">Poetic, evocative ("Perfume of the Mediterranean")</td>
        </tr>
        <tr style="background:#faf8f5;border-bottom:1px solid {BG}">
          <td style="padding:8px 12px;font-weight:700;color:{B}">Rhode</td>
          <td style="padding:8px 12px;color:{LT}">Daily</td>
          <td style="padding:8px 12px;color:{B}">"One really good [product]" series. "ask rhode" FAQ. Single-product focus per email.</td>
          <td style="padding:8px 12px;color:{OL}">All lowercase ("one really good essence")</td>
        </tr>
        <tr style="background:#fff;border-bottom:1px solid {BG}">
          <td style="padding:8px 12px;font-weight:700;color:{B}">OUAI</td>
          <td style="padding:8px 12px;color:{LT}">4×/day (sale)</td>
          <td style="padding:8px 12px;color:{B}">During promo: same offer, 4+ angles (discovery, ICYMI, best sellers, urgency). Puns.</td>
          <td style="padding:8px 12px;color:{OL}">Playful puns + urgency ("ENDS TONIGHT: 20% off")</td>
        </tr>
        <tr style="background:#faf8f5;border-bottom:1px solid {BG}">
          <td style="padding:8px 12px;font-weight:700;color:{B}">Salt & Stone</td>
          <td style="padding:8px 12px;color:{LT}">1–2×/day</td>
          <td style="padding:8px 12px;color:{B}">Emoji in subjects. UGC quote as subject ("You smell incredible"). Image-only emails.</td>
          <td style="padding:8px 12px;color:{OL}">Emoji + seasonal/lifestyle ("Your summer uniform 🌿")</td>
        </tr>
        <tr style="background:#fff">
          <td style="padding:8px 12px;font-weight:700;color:{B}">Nécessaire</td>
          <td style="padding:8px 12px;color:{LT}">2×/day (sale)</td>
          <td style="padding:8px 12px;color:{B}">"Last Chance" subject = highest-open ever. Extreme minimalism: logo + image + CTA only.</td>
          <td style="padding:8px 12px;color:{OL}">Direct ("20% Off Sets") or poetic ("Santal. Now For Your Sink.")</td>
        </tr>
      </table>
    </div>

    <!-- FOOTER -->
    <div style="background:{B};padding:18px 36px;text-align:center">
      <div style="color:rgba(255,255,255,.4);font-size:11px">
        CoBa's Daughter · Daily Marketing Brief · Auto-sent via Gmail API
      </div>
    </div>

  </div>
</body></html>"""


def send_email_brief(service, brief_text: str, today: str) -> str:
    html_body = _render_html(brief_text, today)
    subject   = f"CoBa's Daughter Daily Brief — {today}"

    msg = MIMEMultipart("alternative")
    msg["To"]      = EMAIL_TO
    msg["Cc"]      = EMAIL_CC
    msg["From"]    = "me"
    msg["Subject"] = subject

    # Build recipients string for the "to" field in the API call
    msg.attach(MIMEText(brief_text, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    raw    = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id", "")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    vn_tz = datetime.timezone(datetime.timedelta(hours=7))
    today = datetime.datetime.now(vn_tz).strftime("%A, %B %-d, %Y")

    print(f"[daily_brief] Starting for {today}")

    # 1. Gmail
    service      = None
    brand_emails = {b["name"]: [] for b in REFERENCE_BRANDS}
    try:
        service      = build_gmail_service()
        brand_emails = get_recent_brand_emails(service)
        found = sum(len(v) for v in brand_emails.values())
        print(f"[daily_brief] {found} brand emails fetched")
    except Exception as e:
        print(f"[daily_brief] Gmail unavailable: {e}")

    # 2. Claude brief
    print("[daily_brief] Generating brief…")
    brief = generate_brief(brand_emails, today)
    print(f"[daily_brief] Brief ready ({len(brief)} chars)")

    # 3. Slack DM
    print("[daily_brief] Posting to Slack…")
    try:
        ts = post_to_slack(brief, today)
        print(f"[daily_brief] Slack ts: {ts}")
    except Exception as e:
        print(f"[daily_brief] Slack failed: {e}")

    # 4. Email
    print(f"[daily_brief] Sending email to {EMAIL_TO} (cc {EMAIL_CC})…")
    if service:
        try:
            msg_id = send_email_brief(service, brief, today)
            print(f"[daily_brief] Email sent. id: {msg_id}")
        except Exception as e:
            print(f"[daily_brief] Email failed: {e}")
    else:
        print("[daily_brief] Gmail unavailable — skipping email.")

    print("[daily_brief] Done.")


if __name__ == "__main__":
    main()
