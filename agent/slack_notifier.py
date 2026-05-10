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
    "Beauty":                     "💄",
    "Body Care":                  "🧴",
    "Fashion":                    "👗",
    "Equestrian":                 "🐎",
    "Pop Culture":                "✨",
    "Hollywood":                  "🎬",
    "Film & Music":               "🎵",
    "Cultural Relevancy":         "🌍",
    "Viral Marketing":            "🚀",
    "Social/Hashtags":            "#️⃣",
}

SIGNAL_EMOJI = {"Viral": "🚀", "High": "📈", "Rising": "🌱"}


def _bar(score: float, total: int = 10, filled: str = "█", empty: str = "░") -> str:
    n = round(score / total * 10)
    return filled * n + empty * (10 - n)


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def _divider() -> dict:
    return {"type": "divider"}


def _button_link(label: str, url: str, style: str = "primary") -> dict:
    return {
        "type": "actions",
        "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": label, "emoji": True},
            "url": url,
            "style": style,
        }]
    }


def _build_blocks(report: dict[str, Any], dashboard_url: str = "") -> list[dict]:
    date = report.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    hour = datetime.utcnow().hour
    slot = "9AM" if hour < 15 else "3PM"

    top_trends      = report.get("top_trends", [])
    hot_hashtags    = report.get("hot_hashtags", [])
    spotlight       = report.get("cobas_daughter_spotlight", {})
    hw              = report.get("hollywood_pulse", {})
    eq              = report.get("equestrian_pulse", {})
    tw              = report.get("trend_watch", {})
    brief           = report.get("creator_brief_of_the_week", {})
    viral           = report.get("viral_pulse", {})
    cultural        = report.get("cultural_events_now", [])

    blocks: list[dict] = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HEADER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    blocks.append(_header(f"🐴 CoBa's Daughter — Trend Intelligence · {slot} · {date}"))

    summary = report.get("executive_summary", "")
    if summary:
        blocks.append(_section(f"_{summary}_"))

    # Dashboard link at the very top (most important)
    if dashboard_url:
        blocks.append(_button_link("📊 Open Full Dashboard Report", dashboard_url))

    blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BRAND SPOTLIGHT — big picture
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if spotlight:
        blocks.append(_section("*✦ Brand Spotlight — Your Action Plan*"))
        sp_text = ""
        if spotlight.get("top_opportunity"):
            sp_text += f"*🎯 Top Opportunity:*\n{spotlight['top_opportunity']}\n\n"
        if spotlight.get("equestrian_angle"):
            sp_text += f"*🐎 Equestrian Angle:*\n{spotlight['equestrian_angle']}\n\n"
        if spotlight.get("beauty_body_care_angle"):
            sp_text += f"*✨ Beauty & Body Care:*\n{spotlight['beauty_body_care_angle']}\n\n"
        if spotlight.get("cultural_moment"):
            sp_text += f"*🌍 Cultural Moment:*\n{spotlight['cultural_moment']}"
        blocks.append(_section(sp_text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CULTURAL EVENTS NOW
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if cultural:
        blocks.append(_section("*📅 Cultural Events — Act Now*"))
        ev_lines = []
        for ev in cultural[:4]:
            urgency_emoji = "🔴" if ev.get("urgency") == "Now" else ("🟡" if ev.get("urgency") == "This Week" else "🟢")
            tags = " ".join(ev.get("hashtags", [])[:3])
            ev_lines.append(
                f"{urgency_emoji} *{ev['event']}* — {ev.get('relevance', '')} {tags}"
            )
        blocks.append(_section("\n".join(ev_lines)))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TOP TRENDS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    blocks.append(_section(f"*🏆 Top Trends Right Now — {len(top_trends)} Identified*"))

    for trend in top_trends[:6]:
        rank        = trend.get("rank", "")
        name        = trend.get("trend_name", "")
        cat         = trend.get("category", "")
        v_score     = trend.get("virality_score", 0)
        b_score     = trend.get("brand_relevance_score", 0)
        heat        = trend.get("heat_level", "")
        what        = trend.get("what_is_it", "")
        window      = trend.get("window", "")
        hashtags    = "  ".join(trend.get("key_hashtags", [])[:4])
        br_reason   = trend.get("brand_relevance_reason", "")
        tactics     = trend.get("tactics", {})
        post_now    = tactics.get("post_now", [])
        hooks       = tactics.get("caption_hooks", [])
        ugc         = tactics.get("ugc_brief", "")

        cat_emoji   = CAT_EMOJI.get(cat, "📌")
        heat_emoji  = HEAT_EMOJI.get(heat, "📊")

        text = (
            f"*#{rank} — {cat_emoji} {name}*  ·  `{cat}`\n"
            f"{heat_emoji} `{heat}`  ·  ⏱ _{window}_\n"
            f"Virality `{v_score}/10` {_bar(v_score)}   Brand Fit `{b_score}/10` {_bar(b_score)}\n\n"
            f"_{what}_\n"
        )

        if br_reason:
            text += f"\n💡 *CoBa's Daughter:* {br_reason}\n"

        if post_now:
            text += f"\n*📱 Post Now:*\n"
            for p in post_now[:2]:
                text += f"• {p}\n"

        if ugc:
            text += f"\n*🎬 UGC Brief:* {ugc}\n"

        if hooks:
            text += f"\n*✍️ Hook:* _{hooks[0]}_\n"

        if hashtags:
            text += f"\n{hashtags}"

        blocks.append(_section(text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VIRAL PULSE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if viral:
        vp_text = "*🚀 Viral Pulse*\n"

        viral_products = viral.get("viral_products", [])
        if viral_products:
            vp_text += "\n*Viral Products Right Now:*\n"
            for p in viral_products[:3]:
                vp_text += f"🛒 {p}\n"

        viral_moments = viral.get("viral_moments", [])
        if viral_moments:
            vp_text += "\n*Viral Moments:*\n"
            for m in viral_moments[:3]:
                vp_text += f"⚡ {m}\n"

        social_trends = viral.get("viral_social_trends", [])
        if social_trends:
            vp_text += "\n*Viral Social Trends:*\n"
            for t in social_trends[:3]:
                vp_text += f"📱 {t}\n"

        community = viral.get("community_conversations", [])
        if community:
            vp_text += "\n*Community Conversations:*\n"
            for c in community[:2]:
                vp_text += f"💬 {c}\n"

        blocks.append(_section(vp_text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HOT HASHTAGS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if hot_hashtags:
        lines = ["*#️⃣ Hot Hashtags to Use Today*"]
        for h in hot_hashtags[:12]:
            sig = h.get("posts_signal", "Rising")
            sig_emoji = SIGNAL_EMOJI.get(sig, "🌱")
            lines.append(f"{sig_emoji} `{h['hashtag']}` _{h.get('category', '')}_ — {h.get('how_to_use', '')}")
        blocks.append(_section("\n".join(lines)))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EQUESTRIAN PULSE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if eq:
        eq_text = "*🐎 Equestrian Pulse*\n"
        topics = eq.get("trending_topics", [])
        if topics:
            eq_text += "*Trending in Equestrian:*\n"
            for t in topics[:3]:
                eq_text += f"• {t}\n"
        if eq.get("crossover_opportunity"):
            eq_text += f"\n*Beauty × Equestrian:* {eq['crossover_opportunity']}\n"
        if eq.get("creator_profile"):
            eq_text += f"*Ideal Creator:* {eq['creator_profile']}"
        blocks.append(_section(eq_text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HOLLYWOOD PULSE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if hw:
        moments = hw.get("top_celebrity_moments", [])
        tie_in  = hw.get("brand_tie_in_opportunity", "")
        hw_text = "*🎬 Hollywood Pulse*\n"
        for m in moments[:3]:
            hw_text += f"• {m}\n"
        if tie_in:
            hw_text += f"\n*Brand Tie-In:* {tie_in}"
        blocks.append(_section(hw_text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CREATOR BRIEF
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if brief:
        brief_text = (
            f"*🎥 Creator Brief of the Week*\n"
            f"*Concept:* {brief.get('concept', '')}\n"
            f"*Target Creator:* {brief.get('target_creator_profile', '')}\n"
            f"*Deliverable:* {brief.get('deliverable', '')}\n"
            f"*Opening Hook:* _{brief.get('hook', '')}_"
        )
        dos = brief.get("dos", [])
        donts = brief.get("donts", [])
        if dos:
            brief_text += "\n✅ " + "  ·  ".join(dos[:2])
        if donts:
            brief_text += "\n❌ " + "  ·  ".join(donts[:2])
        blocks.append(_section(brief_text))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TREND WATCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if tw:
        emerging  = tw.get("emerging_to_watch", [])
        fading    = tw.get("fading_trends", [])
        predicted = tw.get("predicted_next_week", "")
        tw_text = "*👀 Trend Watch*\n"
        if emerging:
            tw_text += "*Emerging — Watch These:* " + "  ·  ".join(f"🌱 {t}" for t in emerging[:3]) + "\n"
        if fading:
            tw_text += "*Fading:* " + "  ·  ".join(f"📉 {t}" for t in fading[:2]) + "\n"
        if predicted:
            tw_text += f"*Next Week Prediction:* {predicted}"
        blocks.append(_section(tw_text.strip()))
        blocks.append(_divider())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FOOTER + DASHBOARD LINK AGAIN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if dashboard_url:
        blocks.append(_button_link("📊 View Full Dashboard & Report →", dashboard_url))

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"CoBa's Daughter Trend Intelligence · {date} {slot} · Powered by Claude AI"}
        ]
    })

    return blocks


def send(report: dict[str, Any], bot_token: str, channel_id: str, dashboard_url: str = "") -> bool:
    """Send the trend digest to Slack. Returns True on success."""
    if not bot_token or not channel_id:
        logger.warning("Slack credentials not configured — skipping notification")
        return False

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError

        client = WebClient(token=bot_token)
        blocks = _build_blocks(report, dashboard_url)

        date = report.get("report_date", "")
        fallback = f"CoBa's Daughter Trend Intelligence — {date}"

        # Slack 50-block limit — split into chunks
        chunk_size = 48
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i: i + chunk_size]
            client.chat_postMessage(
                channel=channel_id,
                text=fallback,
                blocks=chunk,
                unfurl_links=False,
            )

        logger.info(f"Slack digest sent ({len(blocks)} blocks) to {channel_id}")
        return True

    except Exception as e:
        logger.error(f"Slack send error: {e}")
        return False
