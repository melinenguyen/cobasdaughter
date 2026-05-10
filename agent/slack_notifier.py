"""Sends the daily trend digest to Slack using Block Kit for rich formatting."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

HEAT_EMOJI = {
    "Peaking Fast": "🔥🔥",
    "Peaking": "🔥",
    "Emerging": "🌱",
    "Mainstream": "📈",
}

CAT_EMOJI = {
    "Beauty": "💄",
    "Fashion": "👗",
    "Pop Culture": "✨",
    "Hollywood": "🎬",
    "Social/Hashtags": "#️⃣",
    "Music": "🎵",
    "Lifestyle": "🌟",
}


def _score_bar(score: float) -> str:
    filled = round(score / 10 * 10)
    return "█" * filled + "░" * (10 - filled)


def _build_blocks(report: dict[str, Any], dashboard_url: str = "") -> list[dict]:
    """Build Slack Block Kit blocks for the daily digest."""
    date = report.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    summary = report.get("executive_summary", "")
    top_trends = report.get("top_trends", [])
    hot_hashtags = report.get("hot_hashtags", [])
    hw = report.get("hollywood_pulse", {})
    tw = report.get("trend_watch", {})
    brief = report.get("creator_brief_of_the_week", {})

    blocks: list[dict] = []

    # ── HEADER ──
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"⚡ US Trend Intelligence — {date}"}
    })

    blocks.append({"type": "divider"})

    # ── EXEC SUMMARY ──
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Today's Pulse*\n{summary}"}
    })

    blocks.append({"type": "divider"})

    # ── TOP TRENDS (top 8) ──
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*🏆 Top Trends Right Now*"}
    })

    for trend in top_trends[:8]:
        rank = trend.get("rank", "")
        name = trend.get("trend_name", "")
        cat = trend.get("category", "")
        score = trend.get("virality_score", 0)
        heat = trend.get("heat_level", "")
        what = trend.get("what_is_it", "")
        window = trend.get("window", "")
        hashtags = " ".join(trend.get("key_hashtags", [])[:3])
        tactics = trend.get("tactics", {})
        post_now = tactics.get("post_now", [])
        ugc = tactics.get("ugc_brief", "")
        hooks = tactics.get("caption_hooks", [])

        cat_emoji = CAT_EMOJI.get(cat, "📌")
        heat_emoji = HEAT_EMOJI.get(heat, "📊")
        score_bar = _score_bar(score)

        trend_text = (
            f"*#{rank} — {cat_emoji} {name}*\n"
            f"{heat_emoji} `{heat}` · Virality: `{score}/10` `{score_bar}`\n"
            f"⏱ Window: _{window}_\n\n"
            f"_{what}_\n\n"
        )

        if post_now:
            trend_text += f"*📱 Post Now:*\n"
            for p in post_now[:2]:
                trend_text += f"• {p}\n"
            trend_text += "\n"

        if ugc:
            trend_text += f"*🎬 UGC Brief:* {ugc}\n\n"

        if hooks:
            trend_text += f"*✍️ Caption Hook:* _{hooks[0]}_\n\n"

        if hashtags:
            trend_text += f"{hashtags}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": trend_text}
        })
        blocks.append({"type": "divider"})

    # ── HOT HASHTAGS ──
    if hot_hashtags:
        hashtag_lines = []
        for h in hot_hashtags[:12]:
            signal = h.get("posts_signal", "")
            sig_emoji = "🚀" if signal == "Viral" else ("📈" if signal == "High" else "🌱")
            hashtag_lines.append(f"{sig_emoji} `{h['hashtag']}` _{h.get('category', '')}_")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*#️⃣ Hot Hashtags*\n" + "\n".join(hashtag_lines)
            }
        })
        blocks.append({"type": "divider"})

    # ── HOLLYWOOD PULSE ──
    if hw:
        moments = hw.get("top_celebrity_moments", [])
        tie_in = hw.get("brand_tie_in_opportunity", "")
        hw_text = "*🎬 Hollywood Pulse*\n"
        for m in moments[:3]:
            hw_text += f"• {m}\n"
        if tie_in:
            hw_text += f"\n*Brand Tie-In:* {tie_in}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": hw_text}
        })
        blocks.append({"type": "divider"})

    # ── CREATOR BRIEF ──
    if brief:
        brief_text = (
            f"*🎥 Creator Brief of the Week*\n"
            f"*Concept:* {brief.get('concept', '')}\n"
            f"*Target:* {brief.get('target_creator_profile', '')}\n"
            f"*Opening Hook:* _{brief.get('hook', '')}_\n"
            f"*Deliverable:* {brief.get('deliverable', '')}"
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": brief_text}
        })
        blocks.append({"type": "divider"})

    # ── TREND WATCH ──
    if tw:
        emerging = tw.get("emerging_to_watch", [])
        predicted = tw.get("predicted_next_week", "")
        tw_text = "*👀 Trend Watch*\n"
        if emerging:
            tw_text += "*Emerging — Watch These:*\n"
            for t in emerging[:3]:
                tw_text += f"🌱 {t}\n"
        if predicted:
            tw_text += f"\n*Next Week Prediction:* {predicted}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": tw_text}
        })

    # ── DASHBOARD LINK ──
    if dashboard_url:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*📊 Full Report:* <{dashboard_url}|View Dashboard>"}
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Generated by TrendPulse AI · {date} · Powered by Claude"}
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

        # Slack has a 50-block limit per message; split if needed
        chunk_size = 48
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i: i + chunk_size]
            fallback = f"US Trend Intelligence Report — {report.get('report_date', '')}"
            client.chat_postMessage(
                channel=channel_id,
                text=fallback,
                blocks=chunk,
            )

        logger.info(f"Slack digest sent to channel {channel_id}")
        return True

    except Exception as e:
        logger.error(f"Slack send error: {e}")
        return False
