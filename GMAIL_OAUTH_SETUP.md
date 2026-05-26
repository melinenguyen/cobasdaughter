# Gmail OAuth Setup — CoBa's Daughter Daily Brief

This guide takes ~10 minutes and only needs to be done **once**.
After completing it, the daily brief will send automatically to
`meline.nguyen@lixibox.com` (CC `phuonglt.job@gmail.com`) every morning at **9 AM GMT+7**.

---

## Overview

```
Your laptop (one-time)          Your server (every day at 9AM)
───────────────────────         ──────────────────────────────
Step 1: Google Cloud            scheduler.py
Step 2: Download credentials  → daily_brief.py
Step 3: Run oauth_setup.py    →   reads GMAIL_TOKEN_JSON env var
Step 4: Paste token to .env   →   scans brand inbox + sends email
```

---

## Step 1 — Create a Google Cloud Project

1. Go to **[console.cloud.google.com](https://console.cloud.google.com)**
   and sign in with `meline.nguyen@lixibox.com` (the sending account).

2. Click **Select a project** → **New Project**.
   - Name: `cobas-daughter-brief` (anything is fine)
   - Click **Create**.

3. Make sure the new project is selected in the top bar.

---

## Step 2 — Enable the Gmail API

1. In the left menu go to **APIs & Services → Library**.
2. Search `Gmail API` → click it → click **Enable**.

---

## Step 3 — Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** → **Create**.
3. Fill in:
   - **App name**: `CoBa's Daughter Brief`
   - **User support email**: `meline.nguyen@lixibox.com`
   - **Developer contact email**: `meline.nguyen@lixibox.com`
4. Click **Save and Continue** through Scopes (leave blank) and Test Users.
5. On **Test Users**, click **+ Add Users** → add `meline.nguyen@lixibox.com` → **Save**.
6. Click **Back to Dashboard**.

> ⚠️ The app stays in "Testing" mode — that is fine.
> It just means only accounts on the test-users list can authorise it.

---

## Step 4 — Create OAuth Credentials

1. Go to **APIs & Services → Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. Application type: **Desktop app**.
4. Name: `cobas-brief-desktop` (anything).
5. Click **Create**.
6. In the popup, click **Download JSON**.
   - The file will be named something like `client_secret_123456-abc.json`.
   - Save it somewhere on your laptop, e.g. `~/Downloads/client_secret.json`.

---

## Step 5 — Run the OAuth Setup Script

Open a terminal **on your laptop** (not the server).

```bash
# 1. Clone / navigate to the project
cd ~/cobasdaughter       # or wherever you cloned it

# 2. Install dependencies if not already
pip install google-auth-oauthlib google-auth google-api-python-client

# 3. Run the helper script
python3 scripts/gmail_oauth_setup.py \
    --credentials ~/Downloads/client_secret.json \
    --save-token  ~/Downloads/gmail_token.json
```

**What happens:**
- A browser window opens automatically.
- Sign in as **`meline.nguyen@lixibox.com`**.
- Click **Allow** (you may see "Google hasn't verified this app" — click **Advanced → Go to cobas-brief-desktop**).
- The browser redirects to `localhost` and the script captures the token.

**The script then prints something like:**

```
✅  Token works. Connected as: meline.nguyen@lixibox.com

════════════════════════════════════════════════════════════
  ✦  YOUR GMAIL_TOKEN_JSON VALUE  ✦
════════════════════════════════════════════════════════════

eyJ0b2tlbiI6ICJ5YTI5Li4uIiwgInJlZnJlc2hfdG9rZW4iOiAiMS8v...

════════════════════════════════════════════════════════════

  Add this to your environment in ONE of these ways:
  ...
```

**Copy the full base64 string** (the long line between the `═` lines).

---

## Step 6 — Add the Token to Your Environment

Pick the option that matches how you run the project:

### Option A — `.env` file (recommended for local / Docker)

Open (or create) `.env` in the project root and add:

```
GMAIL_TOKEN_JSON=eyJ0b2tlbiI6ICJ5YTI5Li4u...  ← paste full string here
```

The `.env` file is already loaded by `python-dotenv` in `agent/config.py`.

### Option B — GitHub Actions secret

If you run the scheduler via GitHub Actions:

1. Go to your repo on GitHub → **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `GMAIL_TOKEN_JSON`
4. Value: paste the full base64 string.
5. Click **Add secret**.

### Option C — Server environment variable

If you run the scheduler on a VPS or cloud server:

```bash
# Add to /etc/environment or your systemd service file
GMAIL_TOKEN_JSON="eyJ0b2tlbiI6..."
```

Or export it in the shell where you start the scheduler:

```bash
export GMAIL_TOKEN_JSON="eyJ0b2tlbiI6..."
python3 scheduler.py
```

---

## Step 7 — Test It

Run the daily brief manually once to confirm emails send:

```bash
# Make sure your .env is populated, then:
python3 scripts/daily_brief.py
```

Expected output:
```
[daily_brief] Starting for Tuesday, May 27, 2026
[daily_brief] 8 brand emails fetched
[daily_brief] Brief ready (1423 chars)
[daily_brief] Posting to Slack…
[daily_brief] Slack ts: 1779780245.845399
[daily_brief] Sending email to meline.nguyen@lixibox.com (cc phuonglt.job@gmail.com)…
[daily_brief] Email sent. id: 18f9a2c3d4e5f678
[daily_brief] Done.
```

After this, the scheduler runs it automatically every day at **9:02 AM GMT+7**.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No refresh_token received` | Go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions), find **cobas-brief-desktop**, click **Remove access**, then re-run the script. |
| `This app is blocked` | Make sure `meline.nguyen@lixibox.com` is added to **Test Users** in Step 3. |
| `invalid_grant` after a few days | Token expired. Re-run `gmail_oauth_setup.py` and paste the new value. (Rare — refresh tokens last indefinitely unless revoked.) |
| `insufficient authentication scopes` | Delete the token, re-run the script — the scopes are now `gmail.readonly + gmail.send + gmail.compose`. |
| Email sends but lands in spam | Add `meline.nguyen@lixibox.com` to your own contacts, and check that the Gmail account has good sending reputation. |
| `GMAIL_TOKEN_JSON not set` | The env var is missing. Double-check `.env` exists in project root and has no typos. |

---

## Token Security Notes

- **Never commit `gmail_token.json` or the base64 string to git.**
  The `.gitignore` already excludes `*.json` credentials files.
- The token grants **read + send** access to `meline.nguyen@lixibox.com`.
  Keep it out of any public repo or CI log output.
- To revoke access at any time: [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

---

## What Gets Sent Every Morning

The daily brief email includes:

- **Brand intel** — what Flamingo Estate, Rhode, OUAI, Salt & Stone, Nécessaire sent in the last 24h + one tactic to steal from each
- **Today's CoBa action** — one concrete Klaviyo task
- **3 quick wins** — under 30 min each
- **Pipeline** — which of this week's 3 emails is next and when it sends
- **Subject line of the day** — one high-converting subject for a cash-cow product
- **Full 3-week campaign plan table** — all 9 emails with subject, preview text, sender, angle, CTA, segment, Smart Send flag
- **Priority checklist** — 9 ranked improvements for open rate & click rate
- **Brand strategy cheat-sheet** — competitor tactics summary

Sent **TO:** `meline.nguyen@lixibox.com` · **CC:** `phuonglt.job@gmail.com`
Scheduled: **every day at 9:02 AM GMT+7** via `scheduler.py`
