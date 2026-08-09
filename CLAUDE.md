# CoBa's Daughter — US Trend Tracking Agent

## What this project is

An automated AI trend intelligence system for **CoBa's Daughter**, a luxury equestrian-meets-beauty lifestyle brand. It runs twice daily via GitHub Actions, collects signals from 8 data sources, synthesizes them with Claude AI, and delivers a branded report to both Slack and email.

**Brand positioning**: Ultra-feminine, equestrian-coded, luxury beauty. Think: riding boots + Charlotte Tilbury + Sol de Janeiro + quiet luxury aesthetic. Competitor set includes Rhode, Drunk Drunk Elephant, Tatcha, Charlotte Tilbury, Sol de Janeiro, Rare Beauty.

---

## Schedule

Two runs per day via GitHub Actions cron (`.github/workflows/daily_trend_report.yml`):
- **9:00 AM GMT+7** → `0 2 * * *` UTC
- **3:00 PM GMT+7** → `0 8 * * *` UTC

Manual trigger available via `workflow_dispatch` with optional `dry_run` flag.

---

## Architecture

```
agent/
├── main.py              # Orchestrator — runs 8 collectors in parallel, analyzes, sends reports
├── config.py            # All env vars + static config (subreddits, feeds, keywords)
├── analyzer.py          # Claude AI synthesis — urgency hierarchy, deduplication, reddit seeding
├── slack_notifier.py    # Slack Block Kit report delivery
├── email_notifier.py    # Gmail SMTP SSL email delivery (HTML)
├── report_generator.py  # Saves JSON + HTML reports to reports/
└── collectors/
    ├── news.py           # 40+ RSS feeds, 8-hour freshness filter, launch/Hollywood buckets
    ├── brand_intel.py    # 18 luxury/trade feeds, 50+ tracked brands, launch detection
    ├── google_trends.py  # Daily trending + keyword interest + rising queries (US)
    ├── twitter.py        # 22 search queries covering beauty, luxury, celebrity, equestrian
    ├── youtube.py        # Trending chart by category + 22 niche searches
    ├── reddit.py         # 30+ subreddits, beauty/fashion/equestrian communities
    ├── instagram.py      # Instagram Graph API (optional — needs Facebook Business App)
    └── cultural_calendar.py  # Upcoming cultural events relevant to brand
```

**Deduplication**: Before each analysis, `main.py` loads `reports/latest.json` from the previous run and injects already-reported trends into the Claude prompt as a "DO NOT REPEAT" list.

**Freshness**: Both `news.py` and `brand_intel.py` filter articles to the last 8 hours using `feedparser`'s `published_parsed` timestamp.

---

## Required GitHub Secrets

| Secret | Purpose |
|--------|----------|
| `ANTHROPIC_API_KEY` | Claude AI analysis (claude-sonnet-4-6 model) |
| `SLACK_BOT_TOKEN` | Slack report delivery |
| `SLACK_CHANNEL_ID` | Comma-separated channel/user IDs |
| `GMAIL_SENDER` | Gmail address for sending email reports |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 |
| `TWITTER_BEARER_TOKEN` | Twitter/X API v2 (optional — degrades gracefully) |
| `REDDIT_CLIENT_ID` | Reddit API (optional — degrades gracefully) |
| `REDDIT_CLIENT_SECRET` | Reddit API (optional) |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API (optional) |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Instagram Graph API (optional) |
| `DASHBOARD_URL` | URL to hosted dashboard (optional, shown in email footer) |

**Hardcoded in workflow** (not secrets):
- `EMAIL_TO: meline.nguyen@lixibox.com`
- `EMAIL_CC: phuonglt.job@gmail.com`

---

## Email Delivery

`agent/email_notifier.py` sends a fully branded HTML email:
- **SMTP**: Gmail SSL, port 465
- **Auth**: App Password (not OAuth — simpler, no token refresh)
- **Subject format**: `US Trend Daily Update - August 9` (current date)
- **Content**: Mirrors Slack report — Brand Spotlight, Brand Launches, Hollywood Pulse, Top Trends with score bars, Viral Pulse, Hot Hashtags, Equestrian Pulse, Reddit Seeding suggestions

Setup guide if Gmail stops working: `GMAIL_APP_PASSWORD_SETUP.md` in repo root.

---

## AI Analysis (`agent/analyzer.py`)

Uses `anthropic` SDK with model `claude-sonnet-4-6`.

**Urgency hierarchy in system prompt**:
1. **POST TODAY** — Breaking brand launches, viral moments, celebrity news <24h
2. **THIS WEEK** — Rising trends with momentum, not yet peaked
3. **WATCH** — Slow-burn signals worth monitoring

**Output JSON sections**:
- `top_trends[]` — with `trend_name`, `category`, `heat_level`, `urgency`, `summary`, `relevance_score`
- `brand_launches_now[]` — breaking product launches with `brand`, `product`, `urgency_badge`
- `hollywood_pulse.top_celebrity_looks[]` — celebrity beauty/fashion moments
- `cobas_daughter_spotlight.brand_to_watch` — one competitor to track this week
- `viral_content_pulse` — TikTok/social virality signals
- `equestrian_pulse` — equestrian crossover moments
- `reddit_seeding[]` — authentic community injection suggestions (see rules below)
- `trend_watch[]` — slower signals to monitor

**Reddit seeding rules (strict)**:
- Never suggest anything that reads like marketing
- Angle must be authentic expertise or genuine recommendation
- Only mention CoBa's Daughter brand name if the thread explicitly asks for brand recommendations
- Focus on equestrian, outdoor beauty, body care, quiet luxury subreddits
- Format: subreddit + thread topic + suggested angle

---

## Collector Notes

### `collectors/news.py`
- 40+ RSS feeds across entertainment, beauty, fashion, Hollywood
- Buckets: `launch_articles`, `hollywood_articles`, `articles`
- Key outlets: People, E! News, THR, Variety, Deadline, Page Six, Allure, WWD, Cosmopolitan, Vogue Business, Business of Fashion, Glossy

### `collectors/brand_intel.py`
- 18 trade/industry feeds (BoF, Vogue Business, PR Newswire Beauty, Luxury Daily, etc.)
- 50+ tracked brands: Hermès, Chanel, LVMH, Charlotte Tilbury, Rhode (Hailey Bieber), Sol de Janeiro, Tatcha, Drunk Elephant, La Mer, Augustinus Bader, etc.
- Buckets: `brand_launches`, `brand_moves`, `luxury_market_news`

### `collectors/reddit.py`
- Pulls from 30+ subreddits in beauty, fashion, equestrian, pop culture
- Passes post titles + snippets to Claude for seeding suggestion generation
- Requires: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` (degrades gracefully if missing)

### `collectors/instagram.py`
- Requires Facebook Business account + Developer App (setup deferred)
- Degrades gracefully if `INSTAGRAM_ACCESS_TOKEN` not set

---

## Reports

Saved to `reports/` directory and committed back to the repo by GitHub Actions:
- `reports/latest.json` — always the most recent run (used for deduplication)
- `reports/YYYY-MM-DD-HHMM.json` — timestamped archive
- Retained as GitHub Actions artifacts for 90 days

---

## Development Branch

Active development branch: `claude/us-trend-tracking-agent-9XKg4`

All changes should go to this branch via PR → merge to `main`. The GitHub Actions workflow runs from `main`.

---

## Pending / Optional Work

- **Reddit API credentials**: Need to register app at reddit.com/prefs/apps — registration was pending as of last session
- **Instagram API**: Requires Facebook Business account + Developer App approval — deferred
- **Email verification**: Confirm email delivery is working in next scheduled run
- **YouTube**: API key is in secrets — monitor next run logs to confirm it's collecting correctly

---

## Key Design Decisions

1. **No external email service** (no SendGrid/Mailgun) — pure Python `smtplib` + Gmail App Password. Simpler, no additional accounts needed.
2. **No database** — reports stored as JSON files in the repo. GitHub Actions commits them back.
3. **Graceful degradation** — every collector checks for its API key and returns empty results with an error message rather than crashing the whole run.
4. **json-repair** — used to parse Claude's JSON output robustly, handles common formatting issues.
5. **8-hour freshness filter** — articles older than 8 hours are excluded from brand_intel and news collectors to avoid surfacing stale stories.
6. **Deduplication between 9AM and 3PM runs** — previous `latest.json` is loaded and injected into the Claude prompt as "DO NOT REPEAT" list.
