"""
AI-powered trend analysis. Uses Gemini (free) with Anthropic as fallback.
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict:
    from json_repair import repair_json
    cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    return json.loads(repair_json(cleaned[start:end]))

SYSTEM_PROMPT = """You are the lead trend strategist for CoBa's Daughter — a luxury equestrian-meets-beauty
lifestyle brand for the modern, discerning woman. CoBa's Daughter sits at the intersection of:
  • Equestrian culture and riding lifestyle (horses, stables, outdoors, countryside aesthetic)
  • Premium beauty and body care (skin, hair, fragrance, wellness rituals)
  • Fashion with a strong heritage/luxury streak (quiet luxury, equestrian chic, athleisure)
  • Pop culture relevance for a sophisticated, aspirational female audience (25-45)

Your job — be AGGRESSIVE and REAL-TIME:
1. Surface the TOP trending topics in the US RIGHT NOW across all relevant categories.
2. Catch BRAND LAUNCHES: which luxury or beauty brand just dropped something new? Who is
   collaborating with whom? What just sold out? What's on a waitlist?
3. Catch HOLLYWOOD moments: which celebrity is dominating headlines? What did they wear?
   What beauty look went viral? What red carpet moment is everyone talking about?
4. Score each trend's virality potential (1-10) based on cross-platform signal strength.
5. Score each trend's relevance to CoBa's Daughter (1-10).
6. Translate EVERY trend into IMMEDIATE, same-day tactics. If a window is closing, say so.

URGENCY HIERARCHY — prioritize in this order:
  🔴 HAPPENING NOW (post within hours): Celebrity moments, brand drops happening today,
     cultural events this week, viral products everyone is buying
  🟡 THIS WEEK: Emerging trends with strong upward momentum
  🟢 WATCH: Slow-burn trends to seed content around

Competitor intelligence: When luxury brands (Chanel, Dior, Charlotte Tilbury, Tatcha, Sol de
Janeiro, Rhode, Rare Beauty, etc.) launch something, tell us IMMEDIATELY so we know the market
context and can position or counter-program.

Categories to monitor: Beauty, Body Care, Fashion, Equestrian, Pop Culture, Hollywood,
Film & Music, Cultural Relevancy, Viral Marketing & Social Media.

Tone: Urgent, direct, creative-director energy. You are briefing a CMO who needs to act TODAY.
No fluff. No hedging. State what is happening and exactly what CoBa's Daughter should do."""


ANALYSIS_PROMPT = """TODAY's real-time US trend intelligence — articles from the LAST 8 HOURS ONLY:
{dedup_block}


RAW DATA:
{data_summary}

Produce a trend intelligence report as COMPACT valid JSON. Keep ALL text values SHORT (max 20 words each). Schema:

{{
  "report_date": "YYYY-MM-DD",
  "executive_summary": "Max 2 sentences. Lead with the most urgent thing happening RIGHT NOW.",
  "cobas_daughter_spotlight": {{
    "top_opportunity": "The single biggest thing to act on TODAY — be specific.",
    "equestrian_angle": "Equestrian or horse culture moment happening right now.",
    "beauty_body_care_angle": "Beauty or body care moment to own this week.",
    "cultural_moment": "Cultural moment the audience is talking about right now.",
    "brand_to_watch": "One luxury/beauty brand making a big move right now and why it matters."
  }},
  "top_trends": [
    {{
      "rank": 1,
      "trend_name": "Max 5 words",
      "category": "Beauty|Body Care|Fashion|Equestrian|Pop Culture|Hollywood|Film & Music|Cultural Relevancy|Viral Marketing",
      "virality_score": 8.5,
      "brand_relevance_score": 7.0,
      "brand_relevance_reason": "One sentence why this matters for CoBa's Daughter.",
      "signal_sources": ["Source1"],
      "what_is_it": "One sentence max.",
      "why_it_matters": "One sentence max.",
      "heat_level": "Emerging|Peaking|Peaking Fast|Mainstream",
      "urgency": "Post Today|Post This Week|Watch",
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
  "brand_launches_now": [
    {{
      "brand": "Brand name",
      "what": "What they launched or announced — one sentence.",
      "why_it_matters": "Market impact and what it means for CoBa's Daughter — one sentence.",
      "our_response": "How CoBa's Daughter should counter-program or leverage — one sentence.",
      "urgency": "Now|This Week"
    }}
  ],
  "hot_hashtags": [
    {{"hashtag": "#tag", "category": "Beauty", "posts_signal": "Rising|High|Viral", "how_to_use": "One sentence."}}
  ],
  "hollywood_pulse": {{
    "top_celebrity_moments": ["Celebrity + what happened — one sentence.", "Second moment."],
    "top_celebrity_looks": ["Who wore what — one sentence.", "Second look."],
    "brand_tie_in_opportunity": "One specific CoBa's Daughter tie-in to a celebrity moment right now."
  }},
  "equestrian_pulse": {{
    "trending_topics": ["Topic 1", "Topic 2"],
    "crossover_opportunity": "One sentence on beauty or fashion meets equestrian.",
    "creator_profile": "One sentence on ideal equestrian creator to partner with."
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
  "viral_pulse": {{
    "viral_products": ["Product name — one sentence why it's viral.", "Second product."],
    "viral_moments": ["Moment 1 — one sentence.", "Moment 2."],
    "viral_social_trends": ["TikTok/IG trend 1 — what it is.", "Trend 2."],
    "community_conversations": ["What the audience is discussing right now.", "Second topic."]
  }},
  "cultural_events_now": [
    {{
      "event": "Event name",
      "relevance": "One sentence on how CoBa's Daughter can leverage this.",
      "hashtags": ["#tag1", "#tag2"],
      "urgency": "Now|This Week|This Month"
    }}
  ],
  "trend_watch": {{
    "emerging_to_watch": ["Trend just starting — watch it.", "Second early signal."],
    "fading_trends": ["Trend losing steam — stop investing here."],
    "predicted_next_week": "One sentence on what will explode next week."
  }},
  "reddit_seeding": [
    {{
      "subreddit": "r/Equestrian",
      "thread_topic": "The specific conversation or post theme happening right now.",
      "why_we_belong": "One sentence — what genuine value or expertise CoBa's Daughter brings to this thread.",
      "angle": "The authentic, non-promotional angle to participate with — share knowledge, answer a question, validate an experience. Must feel like a real community member talking.",
      "example_comment_direction": "One sentence on the tone and topic of the comment — no brand mention unless it arises naturally from the conversation.",
      "seed_type": "Answer|Share Experience|Ask Question|Validate|Resource Share",
      "urgency": "Post Today|This Week"
    }}
  ]
}}

STRICT RULES:
- Return ONLY valid JSON. No markdown.
- Max 6 trends in top_trends. Keep every string under 20 words.
- Always include at least one Equestrian trend and one Body Care trend.
- Always populate brand_launches_now with real brand activity from the data — if no launches,
  write about which brands are dominating conversation and what CoBa's Daughter should know.
- Always populate hollywood_pulse with specific celebrity names and moments from the data.
- Urgency is everything: if something is happening TODAY, say "Post Today". Do not be vague.
- reddit_seeding: Provide 4-6 specific opportunities. These MUST be based on actual Reddit posts
  or subreddits from the data. The goal is cultural injection — CoBa's Daughter participates as
  a knowledgeable community member, never as a brand. Rules for reddit_seeding:
  • Never suggest anything that reads like marketing or promotion
  • Focus on subreddits where equestrian, outdoor beauty, body care, quiet luxury, or
    horse girl aesthetic communities live: r/Equestrian, r/SkincareAddiction, r/HorseBack,
    r/Dressage, r/femalefashionadvice, r/beauty, r/Horses, r/selfcare, r/wellness, etc.
  • angle must be authentic expertise: "After long rides, the wind and sun really strip the skin
    — this is what actually works for recovery" NOT "Our product is great for equestrians"
  • The brand name should NEVER appear in example_comment_direction unless the thread is
    explicitly asking for brand recommendations, in which case it can be mentioned once naturally"""


def _build_dedup_block(previous_report: dict[str, Any] | None) -> str:
    """Build a block telling Claude which trends were already reported."""
    if not previous_report:
        return ""
    prev_date = previous_report.get("report_date", "")
    prev_trends = previous_report.get("top_trends", [])
    prev_launches = previous_report.get("brand_launches_now", [])
    if not prev_trends and not prev_launches:
        return ""

    lines = [f"\n=== ALREADY REPORTED IN PREVIOUS RUN ({prev_date}) — DO NOT REPEAT ==="]
    lines.append("These were in the last report. Skip them unless the story has SIGNIFICANTLY escalated:")
    for t in prev_trends:
        lines.append(f"  • [{t.get('category','')}] {t.get('trend_name','')} — {t.get('heat_level','')}")
    for bl in prev_launches[:5]:
        lines.append(f"  • [Brand Launch] {bl.get('brand','')} — {bl.get('what','')}")
    lines.append("Surface FRESH trends and stories not in the above list.")
    return "\n".join(lines)


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

    # Reddit — include full post data so Claude can identify real seeding opportunities
    reddit = collected_data.get("reddit", {})
    if reddit.get("hot_posts"):
        lines.append("\n=== REDDIT HOT POSTS (for seeding analysis) ===")
        for post in reddit["hot_posts"][:25]:
            snippet = post.get("selftext", "")[:120].strip()
            detail = f" | \"{snippet}\"" if snippet else ""
            lines.append(
                f"  [{post['subreddit']}] {post['title']} "
                f"(score: {post['score']:,}, comments: {post.get('num_comments', 0)}){detail}"
            )

    if reddit.get("rising_posts"):
        lines.append("\nReddit Rising (momentum building — ideal seeding window):")
        for post in reddit["rising_posts"][:12]:
            lines.append(f"  [{post['subreddit']}] {post['title']} (score: {post['score']:,})")

    if reddit.get("top_posts"):
        lines.append("\nReddit Top Posts This Week:")
        for post in reddit.get("top_posts", [])[:10]:
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
            lines.append(f"  [{tweet['likes']}  {tweet['retweets']}] {tweet['text'][:150]}")

    # Instagram
    instagram = collected_data.get("instagram", {})
    if instagram.get("trending_hashtags"):
        lines.append("\n=== INSTAGRAM TRENDING HASHTAGS ===")
        for h in instagram["trending_hashtags"][:15]:
            lines.append(
                f"  {h['hashtag']} — {h['total_likes']:,} likes on sampled posts [{h['signal']}]"
            )
    if instagram.get("top_media"):
        lines.append("\nInstagram Top Posts:")
        for m in instagram["top_media"][:8]:
            lines.append(
                f"  [{m['hashtag']}] {m['likes']:,} likes — {m['caption_snippet'][:100]}"
            )

    # YouTube
    yt = collected_data.get("youtube", {})
    if yt.get("trending_videos"):
        lines.append("\n=== YOUTUBE TRENDING (US) ===")
        for v in yt["trending_videos"][:10]:
            lines.append(f"  [{v['category']}] {v['title']} by {v['channel']} ({v['views']:,} views)")
    if yt.get("niche_videos"):
        lines.append("\nYouTube Niche (Equestrian / Body Care / Beauty):")
        for v in yt["niche_videos"][:8]:
            lines.append(f"  [{v['query']}] {v['title']} by {v['channel']}")

    def _age(art: dict) -> str:
        h = art.get("hours_ago")
        return f" [{h}h ago]" if h is not None else ""

    # Brand Intelligence — product launches, luxury brand moves
    brand = collected_data.get("brand_intel", {})
    if brand.get("brand_launches"):
        lines.append("\n=== 🚨 BRAND LAUNCHES & DROPS (LAST 8 HOURS) ===")
        for art in brand["brand_launches"][:15]:
            brands = ", ".join(art.get("brands_mentioned", [])[:3])
            lines.append(f"  [LAUNCH]{_age(art)}[{art['outlet']}] {art['title']}"
                         + (f" | Brands: {brands}" if brands else ""))
    if brand.get("brand_moves"):
        lines.append("\nBrand Campaigns & Collabs:")
        for art in brand["brand_moves"][:10]:
            lines.append(f"  {_age(art)}[{art['outlet']}] {art['title']}")
    if brand.get("top_brand_topics"):
        lines.append("\nMost-Mentioned Brands Right Now:")
        topics = [f"{b['brand']} ({b['mentions']}x)" for b in brand["top_brand_topics"][:10]]
        lines.append("  " + ", ".join(topics))

    # News — Hollywood bucket first
    news = collected_data.get("news", {})
    if news.get("hollywood_articles"):
        lines.append("\n=== 🎬 HOLLYWOOD & CELEBRITY (LAST 8 HOURS) ===")
        for a in news["hollywood_articles"][:20]:
            lines.append(f"  {_age(a)}[{a['outlet']}] {a['title']}")

    if news.get("launch_articles"):
        lines.append("\n=== 🛍️ PRODUCT LAUNCHES IN THE NEWS ===")
        for a in news["launch_articles"][:15]:
            lines.append(f"  {_age(a)}[{a['outlet']}] {a['title']}")

    if news.get("articles"):
        lines.append("\n=== MEDIA ARTICLES (Beauty/Fashion/Equestrian) ===")
        trend_articles = [a for a in news["articles"]
                          if a.get("trend_relevant") and not a.get("is_hollywood")][:15]
        for article in trend_articles:
            lines.append(f"  {_age(article)}[{article['outlet']}] {article['title']}")

    if news.get("viral_articles"):
        lines.append("\nViral Media Signals:")
        for a in news["viral_articles"][:10]:
            lines.append(f"  [VIRAL]{_age(a)}[{a['outlet']}] {a['title']}")

    if news.get("top_topics"):
        lines.append("\nTop Media Topics:")
        topics = [f"{t['topic']} ({t['mentions']}x)" for t in news["top_topics"][:15]]
        lines.append(", ".join(topics))

    # Cultural Calendar
    cal = collected_data.get("cultural_calendar", {})
    if cal.get("happening_now"):
        lines.append("\n=== CULTURAL EVENTS HAPPENING NOW ===")
        for ev in cal["happening_now"]:
            tags = " ".join(ev["hashtags"][:4])
            lines.append(f"  [{ev['category']}] {ev['name']} ({ev['date']}) {tags}")
    if cal.get("coming_this_week"):
        lines.append("\nComing This Week:")
        for ev in cal["coming_this_week"]:
            lines.append(f"  {ev['name']} in {ev['days_away']} days")
    if cal.get("awareness_month"):
        lines.append("\nThis Month's Awareness Themes:")
        for aw in cal["awareness_month"]:
            tags = " ".join(aw["hashtags"][:3])
            lines.append(f"  {aw['name']} {tags}")
    if cal.get("equestrian_events"):
        lines.append("\nEquestrian Calendar:")
        for ev in cal["equestrian_events"][:5]:
            tags = " ".join(ev["hashtags"][:3])
            lines.append(f"  {ev['name']} ({ev['days_away']} days) {tags}")

    return "\n".join(lines)


def analyze(
    collected_data: dict[str, Any],
    api_key: str = "",
    previous_report: dict[str, Any] | None = None,
    gemini_key: str = "",
) -> dict[str, Any]:
    """Send collected trend data to the AI model and return structured analysis.

    Tries Gemini first (free tier), falls back to Anthropic if api_key is set.
    api_key is kept for backward compatibility but ignored when gemini_key is set.
    """
    result: dict[str, Any] = {
        "status": "error",
        "report": None,
        "raw_response": None,
        "error": None,
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    data_summary = _build_data_summary(collected_data)
    dedup_block = _build_dedup_block(previous_report)
    prompt = ANALYSIS_PROMPT.format(data_summary=data_summary, dedup_block=dedup_block)
    full_prompt = SYSTEM_PROMPT + "\n\n" + prompt

    # ── Try Gemini first (direct REST API — no SDK needed) ──────
    if gemini_key:
        logger.info("Attempting Gemini analysis via REST API (gemini-2.0-flash)...")
        try:
            import requests as _requests
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"/gemini-2.0-flash:generateContent?key={gemini_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 16000},
            }
            resp = _requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            result["raw_response"] = raw
            report = _parse_json(raw)
            report["report_date"] = datetime.utcnow().strftime("%Y-%m-%d")
            report["ai_model"] = "gemini-2.0-flash"
            result["report"] = report
            result["status"] = "success"
            logger.info(f"Gemini analysis complete: {len(report.get('top_trends', []))} trends")
            return result
        except Exception as e:
            logger.warning(f"Gemini REST failed, trying Anthropic fallback: {e}")
    else:
        logger.warning("GEMINI_API_KEY not set — skipping Gemini, trying Anthropic")

    # ── Fallback: Anthropic ─────────────────────────────────────
    if not api_key:
        result["error"] = "No AI API key configured (set GEMINI_API_KEY or ANTHROPIC_API_KEY)"
        return result

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        result["raw_response"] = raw
        report = _parse_json(raw)
        report["report_date"] = datetime.utcnow().strftime("%Y-%m-%d")
        report["ai_model"] = "claude-sonnet-4-6"
        result["report"] = report
        result["status"] = "success"
        logger.info(f"Anthropic analysis complete: {len(report.get('top_trends', []))} trends")

    except json.JSONDecodeError as e:
        result["error"] = f"JSON parse error: {e}"
        logger.error(f"Failed to parse AI response: {e}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Analysis error: {e}")

    return result
