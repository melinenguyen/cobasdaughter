# CoBa's Daughter Brand Pulse — development setup

Status: backend foundation, not yet deployed or connected. Official website confirmed by the owner: https://cobasdaughter.com/. The website describes Vietnamese heritage body care. Earlier café/Melbourne examples were incorrect. Target geography remains unfiltered until confirmed.

The Brand Pulse page requires `BRAND_PULSE_PASSWORD` on its server and uses username `coba`. Serve it over HTTPS. The existing report archive and `/run` routes have their original access behavior: do not expose the entire existing Flask app publicly without a separate access-control layer.

Current coverage: Search Console impressions/clicks for the verified website; matching owned Instagram posts; sampled Reddit submissions; a generic integration contract awaiting selection of a licensed TikTok provider. Google Trends/Ads currently require an import; there is no automatic Trends/Ads connection. Web mentions, comments, OCR, and video transcription are not implemented. Historical coverage is limited to source availability. Geography currently records a label, not a source-side geographic filter.

Reach is unavailable where the provider does not supply it; sentiment is an experimental word-list classifier. The next release must improve source coverage, missing-data handling, retention/deletion processing, and chart units before marketing decisions rely on the dashboard. Collection times are recorded separately from source-data dates, which remain unknown unless explicitly supplied.

I built the dashboard and its daily collection robot in this repository. You only need to connect the accounts it is allowed to read. Do not put a password, API key, or downloaded credential file into a normal GitHub file or message.

## What the parts do

| Part | Plain-English meaning |
| --- | --- |
| Brand Pulse page | The screen where you read the numbers. It lives at `/brand-pulse` once the Flask dashboard is deployed. |
| Database | A private filing cabinet that remembers daily numbers and links. It is not stored in GitHub. |
| Daily workflow | The robot in GitHub Actions. It runs every day at 6:00 AM Ho Chi Minh City time. |
| GitHub secrets | A locked drawer for keys. Only the robot can use them. |

## Step 1 — create the private database

Create a small PostgreSQL database with a managed host such as Supabase, Neon, Render, or Railway. Pick the provider you already use if you have one.

When it gives you a connection string, it will look similar to this:

```text
postgresql://name:password@host.example.com:5432/database?sslmode=require
```

In GitHub open this repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

- Name: `BRAND_PULSE_DATABASE_URL`
- Value: paste the complete PostgreSQL connection string.

Click **Add secret**. This is the one essential setup item. The first daily run creates the tables automatically.

## Step 2 — tell the robot what name and place to look for

Open repository **Settings** → **Secrets and variables** → **Actions** → **Variables** → **New repository variable**.

Create these two variables:

| Name | Value |
| --- | --- |
| `BRAND_PULSE_TERMS` | `CoBa's Daughter,Coba's Daughter,Co Ba's Daughter,#cobasdaughter` |
| `BRAND_PULSE_GEOGRAPHY` | `global` (currently a label; does not filter source data) |

## Step 3 — connect Google Search Console

This measures Google searches that lead to CoBa's Daughter's own website. It does not give global Google search volume.

1. In Google Cloud, create a service account for this robot.
2. Download its JSON key. Do not upload that file to GitHub.
3. Open the key file in a text editor and copy the entire contents, including the `{` and `}`.
4. In GitHub → **Settings** → **Secrets and variables** → **Actions**, create secret `GSC_SERVICE_ACCOUNT_JSON` and paste it.
5. In GitHub → **Variables**, create `GSC_SITE_URL` with the exact verified Search Console property. For the confirmed website, the URL-prefix property is `https://cobasdaughter.com/`. If Search Console uses a Domain property instead, use `sc-domain:cobasdaughter.com`. Do not add `www` unless that is the property actually verified.
6. In Search Console → **Settings** → **Users and permissions**, add the service-account email address as a **Read** user.

## Step 4 — connect Instagram and Reddit

The robot uses only the approved API access you grant.

- **Instagram:** connect a Business or Creator account to the Meta app. Add `INSTAGRAM_ACCESS_TOKEN` as a GitHub secret and `INSTAGRAM_BUSINESS_ACCOUNT_ID` as a GitHub variable. The current collector records matching posts from the connected account, with their permalink and engagement.
- **Reddit:** create approved Data API access. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` as GitHub secrets. The collector searches public posts that match your brand terms and stores the public permalink, title, date, and engagement.

Both API providers can change permissions, rate limits, and retention requirements. Do not replace this with page scraping.

## Step 5 — choose a commercial TikTok source

TikTok's Research API is not appropriate for ordinary commercial brand monitoring. Choose an approved commercial or licensed social-listening provider. Ask it to give you an endpoint that returns a JSON list of matching public videos, each with an ID, URL, caption/title, published date, and engagement/reach where available.

Add:

- `TIKTOK_APPROVED_PROVIDER_URL` as a GitHub variable
- `TIKTOK_APPROVED_PROVIDER_TOKEN` as a GitHub secret

## Step 6 — run it once

1. In GitHub, open the **Actions** tab.
2. Select **CoBa's Daughter Brand Pulse**.
3. Click **Run workflow** → **Run workflow**.
4. Open the run after it finishes. Green means the robot completed. A source marked “Skipped: add …” simply has not been connected yet.

After the first successful run, deploy the existing Flask dashboard on Render, Railway, or another Python host, with the same `BRAND_PULSE_DATABASE_URL` secret. Visit `/brand-pulse` on that site to see real data.

## What updates when

- The GitHub robot starts every day at 06:00 Vietnam time.
- It rechecks the previous seven days so late-arriving social data can appear.
- The dashboard shows the exact latest available date for every source. “Live” means the newest data that the source has made available, not guessed real-time numbers.
- Google Ads keyword volume is usually monthly; import its approved export with `python -m agent.brand_pulse --keyword-csv filename.csv` if you want that separate metric.
