"""
AI-powered trend analysis using Claude.

Takes raw collected data from all sources and returns:
 - Categorised trend cards (Beauty, Fashion, Pop Culture, Hollywood, Social/Hashtags)
 - Virality score (1-10) for each trend
 - Actionable brand tactics (post ideas, UGC brief hooks, asset suggestions, seeding ops)
"""

import json
import logging
from datetime import datetime
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior US brand strategist and trend intelligence analyst specializing in beauty,
fashion, and pop culture for social media virality. You work with data from Google Trends, Reddit, Twitter/X,
YouTube, and media publications to surface the most actionable trends for a consumer brand's marketing team.

Your job is to:
1. Identify the top trending topics in the US across beauty, fashion, pop culture, Hollywood, and social media.
2. Score each trend's virality potential (1-10) based on cross-platform signal strength.
3. Translate each trend into concrete, low-hanging-fruit tactics the brand team can execute IMMEDIATELY.

Tone: Direct, punchy, creative director energy. No fluff. Built for a fast-moving social team."""


ANALYSIS_PROMPT = """Here is today's raw trend intelligence data collected across multiple US platforms:

{data_summary}

Based on this data, produce a structured trend intelligence report in JSON format with this exact schema:

{{
  "report_date": "YYYY-MM-DD",
  "executive_summary": "2-3 sentence punchy overview of what's dominating US culture today",
  "top_trends": [
    {{
      "rank": 1,
      "trend_name": "Short punchy name (max 6 words)",
      "category": "Beauty | Fashion | Pop Culture | Hollywood | Social/Hashtags | Music | Lifestyle",
      "virality_score": 8.5,
      "signal_sources": ["Google Trends", "Reddit", "Twitter"],
      "what_is_it": "1-2 sentence explanation of the trend",
      "why_it_matters": "Why this trend matters for brand relevance and consumer connection",
      "heat_level": "Emerging | Peaking | Peaking Fast | Mainstream",
      "window": "How long this trend window is open (e.g. '24-48 hours', '1-2 weeks', 'ongoing')",
      "key_hashtags": ["#hashtag1", "#hashtag2"],
      "content_angle": "The specific creative angle/narrative your brand should take",
      "tactics": {{
        "post_now": [
          "Specific post idea 1 with format (Reel/Carousel/Story/TikTok) and hook text",
          "Specific post idea 2"
        ],
        "ugc_brief": "Brief hook for creator/UGC brief — what to ask them to film/create and why",
        "asset_creation": "What graphic/video asset the design team should create and the visual direction",
        "seeding": "Who to seed — micro-influencer profile description, aesthetic, follower size, and the send-out angle",
        "caption_hooks": ["Hook line 1", "Hook line 2", "Hook line 3"]
      }}
    }}
  ],
  "hot_hashtags": [
    {{
      "hashtag": "#example",
      "category": "Beauty",
      "posts_signal": "Rising/High/Viral",
      "how_to_use": "One-line tip for using this hashtag authentically"
    }}
  ],
  "hollywood_pulse": {{
    "top_celebrity_moments": ["Celebrity/moment 1", "Celebrity/moment 2"],
    "brand_tie_in_opportunity": "How to connect your brand narrative to current Hollywood conversation"
  }},
  "weekly_content_calendar_suggestions": [
    {{
      "day": "Monday",
      "theme": "Theme name",
      "format": "Reel / Carousel / Story / TikTok",
      "angle": "Specific angle tied to a top trend"
    }}
  ],
  "creator_brief_of_the_week": {{
    "concept": "The one big creator brief the team should send out this week",
    "target_creator_profile": "Describe ideal creator aesthetic/niche/follower count",
    "deliverable": "What they should create (format, length, key message)",
    "hook": "Opening line they should use",
    "dos": ["Do 1", "Do 2"],
    "donts": ["Don't 1", "Don't 2"]
  }},
  "trend_watch": {{
    "emerging_to_watch": ["Early signal trend 1", "Early signal trend 2"],
    "fading_trends": ["Trend that is losing momentum"],
    "predicted_next_week": "What trend we predict will peak next week based on current signals"
  }}
}}

Return ONLY valid JSON. Be specific, be bold, be brand-relevant. Focus on the top 8-12 trends."""


def _build_data_summary(collected_data: dict[str, Any]) -> str:
    """Compress collected data into a readable summary for the AI prompt."""
    lines = []

    # Google Trends
    gt = collected_data.get("google_trends", {})
    if gt.get("daily_trending"):
        lines.append("=== GOOGLE TRENDS (US Daily Trending) ===")
        lines.append(", ".join(gt["daily_trending"][:20]))

    if gt.get("rising_queries"):
        lines.append("\nGoogle Rising Queries:")
        for kw, queries in list(gt["rising_queries"].items())[:5]:
            q_list = [q.get("query", "") for q in queries[:3]]
            lines.append(f"  {kw}: {', '.join(q_list)}")

    # Reddit
    reddit = collected_data.get("reddit", {})
    if reddit.get("hot_posts"):
        lines.append("\n=== REDDIT HOT POSTS (US Pop Culture) ===")
        for post in reddit["hot_posts"][:15]:
            lines.append(f"  [{post['subreddit']}] {post['title']} (score: {post['score']:,})")

    if reddit.get("rising_posts"):
        lines.append("\nReddit Rising:")
        for post in reddit["rising_posts"][:8]:
            lines.append(f"  [{post['subreddit']}] {post['title']}")

    # Twitter
    twitter = collected_data.get("twitter", {})
    if twitter.get("trending_hashtags"):
        lines.append("\n=== TWITTER/X TRENDING HASHTAGS ===")
        tags = [h["hashtag"] for h in twitter["trending_hashtags"][:20]]
        lines.append(", ".join(tags))

    if twitter.get("trending_tweets"):
        lines.append("\nTop Tweets:")
        for tweet in twitter["trending_tweets"][:10]:
            lines.append(f"  [{tweet['likes']}❤ {tweet['retweets']}🔁] {tweet['text'][:150]}")

    # YouTube
    yt = collected_data.get("youtube", {})
    if yt.get("trending_videos"):
        lines.append("\n=== YOUTUBE TRENDING (US) ===")
        for v in yt["trending_videos"][:10]:
            lines.append(f"  [{v['category']}] {v['title']} by {v['channel']} ({v['views']:,} views)")

    # News
    news = collected_data.get("news", {})
    if news.get("articles"):
        lines.append("\n=== MEDIA ARTICLES (Beauty/Fashion/Entertainment) ===")
        trend_articles = [a for a in news["articles"] if a.get("trend_relevant")][:20]
        for article in trend_articles:
            lines.append(f"  [{article['outlet']}] {article['title']}")

    if news.get("top_topics"):
        lines.append("\nTop Media Topics:")
        topics = [f"{t['topic']} ({t['mentions']}x)" for t in news["top_topics"][:15]]
        lines.append(", ".join(topics))

    return "\n".join(lines)


def analyze(collected_data: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Send collected trend data to Claude and return structured analysis."""
    result: dict[str, Any] = {
        "status": "error",
        "report": None,
        "raw_response": None,
        "error": None,
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    if not api_key:
        result["error"] = "ANTHROPIC_API_KEY not configured"
        return result

    data_summary = _build_data_summary(collected_data)
    prompt = ANALYSIS_PROMPT.format(data_summary=data_summary)

    try:
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        result["raw_response"] = raw

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

        report = json.loads(cleaned)
        report["report_date"] = datetime.utcnow().strftime("%Y-%m-%d")
        result["report"] = report
        result["status"] = "success"

        logger.info(f"Analysis complete: {len(report.get('top_trends', []))} trends identified")

    except json.JSONDecodeError as e:
        result["error"] = f"JSON parse error: {e}"
        logger.error(f"Failed to parse Claude response: {e}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Analysis error: {e}")

    return result
