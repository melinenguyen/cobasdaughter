#!/usr/bin/env python3
"""
CoBa's Daughter — Daily Email Marketing Brief Generator
Runs daily at 9AM GMT+7 (2AM UTC). Scans brand inboxes → generates plan → posts to Slack.

Requirements:
  pip install anthropic slack-sdk google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

GitHub Secrets needed:
  ANTHROPIC_API_KEY    — for Claude API calls
  SLACK_BOT_TOKEN      — Slack bot token (xoxb-...)
  SLACK_USER_ID        — Your Slack user ID (e.g. U08V8865GD7)
  GMAIL_TOKEN_JSON     — Gmail OAuth token JSON (base64-encoded)
"""

import os
import json
import base64
import datetime
from anthropic import Anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────
REFERENCE_BRANDS = [
    {"name": "Flamingo Estate",   "query": "from:@flamingoestate.com OR from:@klaviyo.com flamingo estate"},
    {"name": "Rhode",             "query": "from:@rhodeskin.com OR subject:rhode"},
    {"name": "OUAI",              "query": "from:@theouai.com OR from:@email.theouai.com"},
    {"name": "Salt & Stone",      "query": "from:@saltandstone.com OR from:@email.saltandstone.com"},
    {"name": "Nécessaire",        "query": "from:@necessaire.com OR from:@email.necessaire.com"},
]

SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U08V8865GD7")  # meline.nguyen@lixibox.com

CASH_COW_PRODUCTS = [
    "Scrub Duo",
    "Aloe Duo",
    "Gift Bundle",
    "3-in-1 Artisan Soap",
]

# ─── GMAIL HELPERS ────────────────────────────────────────────────────

def build_gmail_service():
    """Build Gmail API service from env-stored OAuth token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_json = os.environ.get("GMAIL_TOKEN_JSON")
    if not token_json:
        raise ValueError("GMAIL_TOKEN_JSON secret not set")

    token_data = json.loads(base64.b64decode(token_json))
    creds = Credentials.from_authorized_user_info(token_data)
    return build("gmail", "v1", credentials=creds)


def get_recent_brand_emails(service, hours_back=24):
    """Fetch emails from all 5 reference brands in the past N hours."""
    results = {}
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    after_epoch = int(cutoff.timestamp())

    for brand in REFERENCE_BRANDS:
        query = f"({brand['query']}) after:{after_epoch}"
        try:
            response = service.users().messages().list(
                userId="me", q=query, maxResults=5
            ).execute()

            messages = response.get("messages", [])
            brand_emails = []

            for msg_ref in messages:
                msg = service.users().messages().get(
                    userId="me",
                    messageId=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]
                ).execute()

                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                brand_emails.append({
                    "subject": headers.get("Subject", "(no subject)"),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                })

            results[brand["name"]] = brand_emails

        except Exception as e:
            results[brand["name"]] = [{"error": str(e)}]

    return results


# ─── BRIEF GENERATOR ──────────────────────────────────────────────────

def generate_brief(brand_emails: dict, today: str) -> str:
    """Use Claude to generate the daily brief from brand email data."""
    client = Anthropic()

    brand_data_text = ""
    for brand_name, emails in brand_emails.items():
        brand_data_text += f"\n### {brand_name}\n"
        if not emails:
            brand_data_text += "No emails in the last 24h.\n"
            continue
        for e in emails:
            if "error" in e:
                brand_data_text += f"  Error fetching: {e['error']}\n"
            else:
                brand_data_text += f"  Subject: {e['subject']}\n"
                brand_data_text += f"  Snippet: {e['snippet'][:200]}\n"
                brand_data_text += "  ---\n"

    prompt = f"""You are the email marketing strategist for CoBa's Daughter, a clean beauty DTC brand launched March 2026 with ~2.5K subscribers.

Today is {today} (Vietnam time, GMT+7).

Cash-cow products to focus on: {', '.join(CASH_COW_PRODUCTS)}.

Brand: CoBa's Daughter. Palette: warm beige, rust (#6b4423), olive (#716a56), dark brown (#2a1f17). Voice: intimate, editorial, artisan.

Current goals: Improve open rate + click rate (both currently poor). Send 3 campaigns/week.

Here are emails from the 5 reference brands in the last 24 hours:
{brand_data_text}

Generate a concise daily brief for Slack with these sections:
1. **📬 Brand Intel** — For each brand that sent an email: their angle today + 1 tactic to steal for CoBa's Daughter. Max 2 sentences per brand.
2. **📅 Today's CoBa Action** — What specific thing should be worked on today (template, subject line, campaign setup). Be concrete.
3. **⚡ Quick Wins (3 items)** — Three things that can be done in under 30 min to improve this week's campaign performance.
4. **📊 Pipeline Reminder** — What campaigns are due this week (from June 2-8 plan: Scrub Duo Tue, Aloe Duo+Soap Thu, Bundle Sat).
5. **✦ Subject Line of the Day** — One high-converting subject line for any of the 4 cash-cow products, with a 1-line reason why it works.

Keep each section tight. Use Slack markdown (**bold**, _italic_). Total message under 1500 chars. No fluff."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


# ─── SLACK SENDER ─────────────────────────────────────────────────────

def post_to_slack(brief_text: str, today: str):
    """Post the daily brief as a DM to the user."""
    from slack_sdk import WebClient

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN secret not set")

    client = WebClient(token=token)

    header = f"*📬 CoBa's Daughter — Daily Conversion Brief*\n_{today} · 9:00 AM GMT+7 · Auto-generated_\n\n"
    footer = "\n\n_────────────────────_\n_Full plan: `reports/email_plan_2026-05-25_conversion.html`_"

    full_message = header + brief_text + footer

    response = client.chat_postMessage(
        channel=SLACK_USER_ID,
        text=full_message,
        mrkdwn=True
    )

    return response["ts"]


# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    vn_tz_offset = datetime.timezone(datetime.timedelta(hours=7))
    today = datetime.datetime.now(vn_tz_offset).strftime("%A, %B %-d, %Y")

    print(f"[daily_brief] Starting brief generation for {today}")

    # 1. Fetch brand emails
    print("[daily_brief] Fetching Gmail inbox...")
    try:
        service = build_gmail_service()
        brand_emails = get_recent_brand_emails(service)
        found = sum(len(v) for v in brand_emails.values())
        print(f"[daily_brief] Found {found} brand emails across 5 brands")
    except Exception as e:
        print(f"[daily_brief] Gmail fetch failed: {e}")
        brand_emails = {brand["name"]: [] for brand in REFERENCE_BRANDS}

    # 2. Generate brief
    print("[daily_brief] Generating brief with Claude...")
    brief = generate_brief(brand_emails, today)
    print(f"[daily_brief] Brief generated ({len(brief)} chars)")

    # 3. Post to Slack
    print("[daily_brief] Posting to Slack...")
    ts = post_to_slack(brief, today)
    print(f"[daily_brief] Posted to Slack. Message ts: {ts}")

    print("[daily_brief] Done.")


if __name__ == "__main__":
    main()
