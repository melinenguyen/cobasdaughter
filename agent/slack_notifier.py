"""Sends the CoBa's Daughter trend digest to Slack using Block Kit."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

HEAT_EMOJI = {
    "Peaking Fast": "🔥🔥",
    "Peaking":      "🔥",
    "Emerging":     "🌱",
    "Mainstream":   "📈",
}

CAT_EMOJI = {
    "Beauty":             "💄",
    "Body Care":          "🧴",
    "Fashion":            "👗",
    "Equestrian":         "🐎",
    "Pop Culture":        "✨",
    "Hollywood":          "🎬",
    "Film & Music":       "🎵",
    "Cultural Relevancy": "🌍",
    "Viral Marketing":    "🚀",
    "Social/Hashtags":    "#️⃣",
}

SIGNAL_EMOJI = {"Viral": "🚀", "High": "📈", "Rising": "🌱"}


def _dots(score: float, total: int = 10) -> str:
    """Render a clean dot bar — no ugly Unicode blocks."""
    filled = round(score / total * 10)
    return "●" * filled + "○" * (10 - filled)


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def _divider() -> dict:
    return {"type": "divider"}


def _link_section(label: str, url: str) -> dict:
    """Text-based link that always renders (unlike action buttons which need valid URLs)."""
    return _section(f"*{label}* → <{url}|Open Report>")


def _build_blocks(report: dict[str, Any], dashboard_url: str = "", repo_url: str = "") -> list[dict]:
    date        = report.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    # Determine slot using GMT+7 local hour
    gmt7_hour   = (datetime.utcnow().hour + 7) % 24
    slot        = "9AM" if gmt7_hour < 12 else "3PM"
    top_trends   = report.get("top_trends", [])
    hot_hashtags = report.get("hot_hashtags", [])
    spotlight    = report.get("cobas_daughter_spotlight", {})
    hw           = report.get("hollywood_pulse", {})
    eq           = report.get("equestrian_pulse", {})
    tw           = report.get("trend_watch", {})
    brief        = report.get("creator_brief_of_the_week", {})
    viral        = report.get("viral_pulse", {})
    cultural     = report.get("cultural_events_now", [])
    brand_launches = report.get("brand_launches_now", [])

    # Best available link: dashboard > repo reports folder
    report_link = dashboard_url or repo_url or ""

    blocks: list[dict] = []

    # ── HEADER ──────────────────────────────────────────────
    blocks.append(_header(f"🐴 CoBa's Daughter — Trend Intelligence · {slot} · {date}"))
    summary = report.get("executive_summary", "")
    if summary:
        blocks.append(_section(f"_{summary}_"))

    # Dashboard link — always at the very top as plain text link (always visible)
    if report_link:
        blocks.append(_section(f"📊 *Full Dashboard & Report* → <{report_link}|View Now>"))

    blocks.append(_divider())

    # ── TREND SUMMARY TABLE ──────────────────────────────────
    if top_trends:
        table_lines = ["*📋 Trends At A Glance*\n"]
        for t in top_trends:
            cat_em  = CAT_EMOJI.get(t.get("category", ""), "📌")
            heat_em = HEAT_EMOJI.get(t.get("heat_level", ""), "")
            v       = t.get("virality_score", 0)
            b       = t.get("brand_relevance_score", 0)
            table_lines.append(
                f"*#{t.get('rank')}* {cat_em} *{t.get('trend_name')}* · "
                f"`{t.get('category')}` · {heat_em} `{t.get('heat_level')}` · "
                f"⏱ _{t.get('window')}_ · "
                f"Virality `{v}` · Brand Fit `{b}`"
            )
        blocks.append(_section("\n".join(table_lines)))
        blocks.append(_divider())

    # ── BRAND SPOTLIGHT ─────────────────────────────────────
    if spotlight:
        sp_text = "*✦ CoBa's Daughter — Your Action Plan Today*\n\n"
        if spotlight.get("top_opportunity"):
            sp_text += f"*🎯 Top Opportunity:* {spotlight['top_opportunity']}\n"
        if spotlight.get("equestrian_angle"):
            sp_text += f"*🐎 Equestrian:* {spotlight['equestrian_angle']}\n"
        if spotlight.get("beauty_body_care_angle"):
            sp_text += f"*✨ Beauty & Body Care:* {spotlight['beauty_body_care_angle']}\n"
        if spotlight.get("cultural_moment"):
            sp_text += f"*🌍 Cultural Moment:* {spotlight['cultural_moment']}\n"
        if spotlight.get("brand_to_watch"):
            sp_text += f"*👀 Brand to Watch:* {spotlight['brand_to_watch']}"
        blocks.append(_section(sp_text.strip()))
        blocks.append(_divider())

    # ── BRAND LAUNCHES NOW ───────────────────────────────────
    if brand_launches:
        bl_lines = ["*🛍️ Brand Launches & Moves — Right Now*"]
        for launch in brand_launches[:4]:
            urgency = launch.get("urgency", "")
            badge   = "🔴" if urgency == "Now" else "🟡"
            bl_lines.append(
                f"{badge} *{launch.get('brand','')}* — {launch.get('what','')}\n"
                f"   ↳ *Our response:* {launch.get('our_response','')}"
            )
        blocks.append(_section("\n".join(bl_lines)))
        blocks.append(_divider())

    # ── CULTURAL EVENTS ─────────────────────────────────────
    if cultural:
        ev_lines = ["*📅 Cultural Events — Act Now*"]
        for ev in cultural[:4]:
            urgency = ev.get("urgency", "")
            badge   = "🔴" if urgency == "Now" else ("🟡" if urgency == "This Week" else "🟢")
            tags    = "  ".join(ev.get("hashtags", [])[:3])
            ev_lines.append(f"{badge} *{ev['event']}* `{urgency}` — {ev.get('relevance', '')}  {tags}")
        blocks.append(_section("\n".join(ev_lines)))
        blocks.append(_divider())

    # ── TOP TRENDS (full detail) ─────────────────────────────
    blocks.append(_section(f"*🏆 Top Trends — {len(top_trends)} Identified*"))

    for trend in top_trends[:6]:
        v_score  = trend.get("virality_score", 0)
        b_score  = trend.get("brand_relevance_score", 0)
        heat     = trend.get("heat_level", "")
        cat      = trend.get("category", "")
        tactics  = trend.get("tactics", {})
        post_now = tactics.get("post_now", [])
        hooks    = tactics.get("caption_hooks", [])
        ugc      = tactics.get("ugc_brief", "")
        hashtags = "  ".join(trend.get("key_hashtags", [])[:4])

        text = (
            f"*#{trend.get('rank')} — {CAT_EMOJI.get(cat,'📌')} {trend.get('trend_name')}*  ·  `{cat}`\n"
            f"{HEAT_EMOJI.get(heat,'')} `{heat}`  ·  ⏱ _{trend.get('window')}_\n"
            f"Virality `{v_score}/10`  {_dots(v_score)}\n"
            f"Brand Fit `{b_score}/10`  {_dots(b_score)}\n\n"
            f"_{trend.get('what_is_it','')}_\n"
        )
        if trend.get("brand_relevance_reason"):
            text += f"\n💡 *CoBa's Daughter:* {trend['brand_relevance_reason']}\n"
        if post_now:
            text += "\n*📱 Post Now:*\n" + "".join(f"• {p}\n" for p in post_now[:2])
        if ugc:
            text += f"\n*🎬 UGC Brief:* {ugc}\n"
        if hooks:
            text += f"\n*✍️ Hook:* _{hooks[0]}_\n"
        if hashtags:
            text += f"\n{hashtags}"

        blocks.append(_section(text.strip()))
        blocks.append(_divider())

    # ── VIRAL PULSE ─────────────────────────────────────────
    if viral:
        vp = "*🚀 Viral Pulse*\n"
        for label, key, em in [
            ("Viral Products", "viral_products", "🛒"),
            ("Viral Moments",  "viral_moments",  "⚡"),
            ("Social Trends",  "viral_social_trends", "📱"),
            ("Community",      "community_conversations", "💬"),
        ]:
            items = viral.get(key, [])
            if items:
                vp += f"\n*{em} {label}:*\n" + "".join(f"• {i}\n" for i in items[:3])
        blocks.append(_section(vp.strip()))
        blocks.append(_divider())

    # ── HOT HASHTAGS ────────────────────────────────────────
    if hot_hashtags:
        lines = ["*#️⃣ Hot Hashtags to Use Today*"]
        for h in hot_hashtags[:12]:
            sig = h.get("posts_signal", "Rising")
            lines.append(
                f"{SIGNAL_EMOJI.get(sig,'🌱')} `{h['hashtag']}` _{h.get('category','')}_ — {h.get('how_to_use','')}"
            )
        blocks.append(_section("\n".join(lines)))
        blocks.append(_divider())

    # ── EQUESTRIAN PULSE ────────────────────────────────────
    if eq:
        eq_text = "*🐎 Equestrian Pulse*\n"
        topics = eq.get("trending_topics", [])
        if topics:
            eq_text += "*Trending:* " + "  ·  ".join(topics[:3]) + "\n"
        if eq.get("crossover_opportunity"):
            eq_text += f"*Beauty × Equestrian:* {eq['crossover_opportunity']}\n"
        if eq.get("creator_profile"):
            eq_text += f"*Ideal Creator:* {eq['creator_profile']}"
        blocks.append(_section(eq_text.strip()))
        blocks.append(_divider())

    # ── HOLLYWOOD PULSE ─────────────────────────────────────
    if hw:
        hw_text = "*🎬 Hollywood Pulse — Right Now*\n"
        moments = hw.get("top_celebrity_moments", [])
        looks   = hw.get("top_celebrity_looks", [])
        for m in moments[:3]:
            hw_text += f"• {m}\n"
        if looks:
            hw_text += "\n*👗 Celebrity Looks:*\n"
            for lk in looks[:2]:
                hw_text += f"• {lk}\n"
        if hw.get("brand_tie_in_opportunity"):
            hw_text += f"\n*CoBa's Tie-In:* {hw['brand_tie_in_opportunity']}"
        blocks.append(_section(hw_text.strip()))
        blocks.append(_divider())

    # ── CREATOR BRIEF ────────────────────────────────────────
    if brief:
        text = (
            f"*🎥 Creator Brief of the Week*\n"
            f"*Concept:* {brief.get('concept','')}\n"
            f"*Target:* {brief.get('target_creator_profile','')}\n"
            f"*Deliverable:* {brief.get('deliverable','')}\n"
            f"*Hook:* _{brief.get('hook','')}_"
        )
        dos   = brief.get("dos", [])
        donts = brief.get("donts", [])
        if dos:
            text += "\n✅ " + "  ·  ".join(dos[:2])
        if donts:
            text += "\n❌ " + "  ·  ".join(donts[:2])
        blocks.append(_section(text))
        blocks.append(_divider())

    # ── REDDIT SEEDING ───────────────────────────────────────
    reddit_seeds = report.get("reddit_seeding", [])
    if reddit_seeds:
        seed_lines = ["*🌱 Reddit Seeding — Low-Hanging Fruit*\n_Participate authentically, never promote_\n"]
        for seed in reddit_seeds[:5]:
            urgency  = seed.get("urgency", "")
            badge    = "🔴" if urgency == "Post Today" else "🟡"
            seed_type = seed.get("seed_type", "")
            seed_lines.append(
                f"{badge} *{seed.get('subreddit','')}* `{seed_type}`\n"
                f"   *Thread:* {seed.get('thread_topic','')}\n"
                f"   *Why we belong:* {seed.get('why_we_belong','')}\n"
                f"   *Angle:* _{seed.get('angle','')}_"
            )
        blocks.append(_section("\n".join(seed_lines)))
        blocks.append(_divider())

    # ── TREND WATCH ─────────────────────────────────────────
    if tw:
        tw_text = "*👀 Trend Watch*\n"
        emerging = tw.get("emerging_to_watch", [])
        fading   = tw.get("fading_trends", [])
        if emerging:
            tw_text += "*Emerging:* " + "  ·  ".join(f"🌱 {t}" for t in emerging[:3]) + "\n"
        if fading:
            tw_text += "*Fading:* "   + "  ·  ".join(f"📉 {t}" for t in fading[:2]) + "\n"
        if tw.get("predicted_next_week"):
            tw_text += f"*Next Week:* {tw['predicted_next_week']}"
        blocks.append(_section(tw_text.strip()))
        blocks.append(_divider())

    # ── FOOTER + LINK AGAIN ──────────────────────────────────
    if report_link:
        blocks.append(_section(f"📊 *Full Dashboard & Report* → <{report_link}|View Now>"))

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
                       "text": f"CoBa's Daughter Trend Intelligence · {date} {slot} · Powered by Claude AI"}]
    })

    return blocks


def send(
    report: dict[str, Any],
    bot_token: str,
    channel_ids: str,          # comma-separated: "U123,U456,C789"
    dashboard_url: str = "",
    repo_url: str = "",
) -> bool:
    """Send the trend digest to one or more Slack channels/users. Returns True if all succeed."""
    if not bot_token or not channel_ids:
        logger.warning("Slack credentials not configured — skipping notification")
        return False

    recipients = [c.strip() for c in channel_ids.split(",") if c.strip()]
    if not recipients:
        return False

    try:
        from slack_sdk import WebClient

        client  = WebClient(token=bot_token)
        blocks  = _build_blocks(report, dashboard_url=dashboard_url, repo_url=repo_url)
        fallback = f"CoBa's Daughter Trend Intelligence — {report.get('report_date', '')}"
        all_ok  = True

        for channel in recipients:
            try:
                for i in range(0, len(blocks), 48):
                    client.chat_postMessage(
                        channel=channel,
                        text=fallback,
                        blocks=blocks[i: i + 48],
                        unfurl_links=False,
                    )
                logger.info(f"Slack digest sent to {channel}")
            except Exception as e:
                logger.error(f"Slack send error for {channel}: {e}")
                all_ok = False

        return all_ok

    except Exception as e:
        logger.error(f"Slack error: {e}")
        return False
