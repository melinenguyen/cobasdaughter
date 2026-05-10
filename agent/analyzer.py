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


ANALYSIS_PROMPT = """Here is today's raw US trend intelligence data:

{data_summary}

Produce a trend intelligence report as COMPACT valid JSON. Keep ALL text values SHORT (max 20 words each). Schema:

{{
  "report_date": "YYYY-MM-DD",
  "executive_summary": "Max 2 sentences.",
  "top_trends": [
    {{
      "rank": 1,
      "trend_name": "Max 5 words",
      "category": "Beauty|Fashion|Pop Culture|Hollywood|Social/Hashtags|Music|Lifestyle",
      "virality_score": 8.5,
      "signal_sources": ["Source1"],
      "what_is_it": "One sentence max.",
      "why_it_matters": "One sentence max.",
      "heat_level": "Emerging|Peaking|Peaking Fast|Mainstream",
      "window": "e.g. 48 hours",
      "key_hashtags": ["#tag1", "#tag2"],
      "content_angle": "One sentence max.",
      "tactics": {{
        "post_now": ["Format + hook in one sentence.", "Second idea one sentence."],
        "ugc_brief": "One sentence creator direction.",
        "asset_creation": "One sentence visual direction.",
        "seeding": "One sentence seeding target.",
        "caption_hooks": ["Hook 1", "Hook 2", "Hook 3"]
      }}
    }}
  ],
  "hot_hashtags": [
    {{"hashtag": "#tag", "category": "Beauty", "posts_signal": "Rising|High|Viral", "how_to_use": "One sentence."}}
  ],
  "hollywood_pulse": {{
    "top_celebrity_moments": ["Moment 1", "Moment 2"],
    "brand_tie_in_opportunity": "One sentence."
  }},
  "weekly_content_calendar_suggestions": [
    {{"day": "Monday", "theme": "Theme", "format": "Reel", "angle": "One sentence."}}
  ],
  "creator_brief_of_the_week": {{
    "concept": "One sentence.",
    "target_creator_profile": "One sentence.",
    "deliverable": "One sentence.",
    "hook": "Opening line.",
    "dos": ["Do 1", "Do 2"],
    "donts": ["Dont 1", "Dont 2"]
  }},
  "trend_watch": {{
    "emerging_to_watch": ["Trend 1", "Trend 2"],
    "fading_trends": ["Fading trend"],
    "predicted_next_week": "One sentence."
  }}
}}

STRICT RULES: Return ONLY valid JSON. No markdown. Max 5 trends. Keep every string under 20 words."""


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
            max_tokens=16000,
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
