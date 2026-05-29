# Canva Runbook — Turn the 100-ad system into finished, exported ads

This takes the two CSVs in this folder and produces 100 designs per ratio, then batch-exports them. Everything lives in your Canva account already.

## What's already created in your Canva

| Asset | Ratio / size | Open to edit |
|-------|--------------|--------------|
| 📁 **Campaign folder** | — | https://www.canva.com/folder/FAHLD0UsRxk |
| **1:1 Master** (`DAHLD0dSkKo`) | 1080 × 1080 | https://www.canva.com/d/Itb826MYvnkbrTK |
| **9:16 Master** (`DAHLD8DRCK8`) | 1080 × 1920 | https://www.canva.com/d/gXvxXgYWga0WIFU |

> These are AI-generated starting points styled to brief (cream/oat palette, Plus Jakarta Sans, premium minimal). **Polish them once** before bulk-running — that polish then applies to all 100. There is also a leftover 4:5 draft (`DAHLD6E2IGg`) you can delete.

## Data files in this folder

- `bulk-create-1x1.csv` → use with the **1:1 Master**
- `bulk-create-9x16.csv` → use with the **9:16 Master**
- Columns (these become the connected fields): `headline, subhead, badge, cta, product` (+ `ad_id, funnel, angle, concept, visual` for reference; `visual` is art direction, don't connect it to a text layer).

---

## Step 1 — Polish each master once (≈15 min)

In each master:
1. **Font:** select all text → set to **Plus Jakarta Sans**. (Headline ~Bold, Subhead ~Regular, Badge ~SemiBold, CTA ~SemiBold.) If you have a Brand Kit with it, apply that.
2. **Colors:** lock to the brand palette (cream/oat background, espresso-brown text, taupe accents). Use your Brand Kit if set.
3. **Image frame:** make the photo area a **frame/placeholder** (Elements → Frames) so Bulk Create / manual swap is clean. You'll drop in the Pinterest/product shots per the `visual` column.
4. **9:16 safe zones:** keep headline + CTA inside the **middle ~80%** — top ~250px and bottom ~310px get covered by the Stories/Reels UI. Don't let the badge or CTA hug the very bottom.
5. **Name the text layers** Headline / Subhead / Badge / CTA / Product (Layers panel) so connecting data is fast.

## Step 2 — Bulk Create (the part that makes 100 at once)

> Bulk Create is a Canva **Pro/Teams** feature. In the editor it's **Apps → "Bulk Create"** (a.k.a. "Bulk create").

1. Open the **1:1 Master**.
2. **Apps → Bulk Create → Upload CSV** → choose `bulk-create-1x1.csv`.
3. For each text layer: right-click → **Connect data** → pick the matching column (Headline→`headline`, Subhead→`subhead`, Badge→`badge`, CTA→`cta`, Product→`product`).
4. Click **Continue → Generate** → select all 100 rows → **Generate pages**. You now have 100 pages, one per ad.
5. Repeat in the **9:16 Master** with `bulk-create-9x16.csv`.

> Bulk Create fills **text** only. Photos are added after (Step 3). If you'd rather auto-fill images too, add an image column with public image URLs and connect it to the frame — but hand-picking the Pinterest shots per angle will look better.

## Step 3 — Drop in the visuals

Work **angle by angle** (the pages are grouped in CSV order). Use the `visual` column as the shot brief. Upload your Pinterest + product photography to **Uploads**, then drag into each page's image frame. Tips:
- Reuse one strong photo across the 8 concepts of an angle to isolate the **hook** as the test variable.
- Keep skin/product shots bright and warm to match the palette.

## Step 4 — Batch export

1. **Share → Download.**
2. Format **PNG** (or JPG for smaller files), tick **"Select pages"** if you want subsets.
3. Download → you get all pages as a numbered set (or a zip). File order follows CSV order, so `ad_id` (e.g. `BOF-041`) lines up with the row.
4. Do the same in the 9:16 design.

> Programmatic export is also possible per-design via the API/MCP (`export-design`), but the in-editor "Download all pages" is the fastest path for 100.

## Step 5 — Zodiac expansion (`B-ZODIAC`)

The CSV ships **Gemini, Cancer, Leo, Virgo** + 2 generic `[SIGN]15` rows. To cover all 12 signs, duplicate the generic row 12× and swap the sign + code (ARIES15, TAURUS15, …, PISCES15). **Important:** each sign's ad must be served only to users whose birthday falls in that window — set that gate at the **ad-set audience** level, not in the creative.

---

## Naming & handoff convention

Export filenames / ad names: `CBD_BROAD_<ad_id>_<ratio>` → e.g. `CBD_BROAD_BOF-041_1x1`.
This keeps the Meta upload mapped back to `STRATEGY.md` angles and the `100-ads.md` matrix for reporting.

## Guardrails baked in (don't break these)

- **One promo per BOF ad.** Never add a second offer to a creative.
- **MOF ads carry no price** — only the RTB badge.
- **Single-minded:** one headline idea per ad. If you're tempted to add a line, make it a new ad instead.
- **Birthday-horoscope ads are audience-gated** by sign.
