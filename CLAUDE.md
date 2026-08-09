# CoBa's Daughter — Automation Repo (working copy)

Local clone of **github.com/melinenguyen/cobasdaughter** (public, default branch `main`).
This is the working copy for the **Daily Email War Room brief**. Edit here, commit, push to `main` —
GitHub Actions is what actually runs the job, so nothing takes effect until it's pushed.

## The daily brief

| | |
|---|---|
| Script | `scripts/daily_brief.py` (~970 lines) |
| Workflow | `.github/workflows/daily-email-brief.yml` |
| Schedule | cron `0 2 * * *` = 02:00 UTC = **09:00 GMT+7** |
| Manual run | Actions tab → "Daily Email Marketing Brief" → Run workflow |

Pipeline: Gmail IMAP scan (12 reference brands + all `List-Unsubscribe` senders, 5-day rolling
window) → Klaviyo recent-campaign context → Claude (`claude-sonnet-4-6`, 8000 max tokens) writes a
Slack brief **plus 5 full email templates** → Slack DM (brief only) + HTML email to
meline.nguyen@lixibox.com cc phuonglt.job@gmail.com.

The Claude response is one blob split on `===EMAIL 1===` … `===EMAIL 5===`. Part 0 is Slack mrkdwn;
parts 1–5 are parsed by regex in `_parse_email_template()` and rendered as HTML mockup cards.
**If you change the prompt's output format, update the regexes in `_parse_email_template()` too** —
they silently produce empty cards on mismatch.

## Credentials

`GMAIL_APP_PASSWORD` does double duty: IMAP inbox scan *and* SMTP send. One bad password kills both
halves of the job. It is also shared with `daily_trend_report.yml`, so a rotation breaks two jobs.

Secrets live in repo Settings → Secrets → Actions (write-only; can't be read back).
Referenced but **not currently configured**: `GMAIL_TOKEN_JSON`, `CANVA_*` — these resolve to empty
strings, and the code degrades gracefully (Canva falls back to text placeholders).

## Failure modes to know

- **Silent failures.** `main()` catches every step's exception and prints it, so the workflow exits 0
  and reports green even when Slack and email both failed. Green ≠ delivered. Read the run log.
- Gmail auth broke 2026-08-03 (app password revoked) and went unnoticed for 7 days because of the
  above. Symptom in logs: `Gmail IMAP failed: [AUTHENTICATIONFAILED]` + `Email failed: (535 …)`.
- When the inbox scan returns nothing, the brief still sends — with a `⚠️` warning prepended to the
  Slack section and an inbox section written from no real data.

## Checking on it

```bash
# recent runs (needs a GitHub token with repo scope)
curl -sS -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/melinenguyen/cobasdaughter/actions/workflows/daily-email-brief.yml/runs?per_page=5"

# logs for one run
curl -sSL -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/melinenguyen/cobasdaughter/actions/runs/<RUN_ID>/logs" -o logs.zip
```

## Local runs

Create `.env` (gitignored) with the vars this script actually reads — note the repo's `.env.example`
is for the *trend* agent and doesn't cover these:

```
ANTHROPIC_API_KEY=
DAILY_BRIEF_SLACK_TOKEN=      # falls back to SLACK_BOT_TOKEN
SLACK_USER_ID=U08V8865GD7
GMAIL_APP_PASSWORD=           # for meline.nguyen@lixibox.com — IMAP scan + SMTP send
KLAVIYO_PRIVATE_API_KEY=      # optional
```

```bash
set -a && source .env && set +a && python3 scripts/daily_brief.py
```

This sends for real — Slack DM and email both go out. To dry-run, comment out the Slack and email
calls at the bottom of `main()` first.
