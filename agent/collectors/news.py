import logging
import re
import requests
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    # Beauty & Skincare
    "Allure":           "https://www.allure.com/feed/rss",
    "Byrdie Beauty":    "https://www.byrdie.com/news-rss",
    "Cosmopolitan":     "https://www.cosmopolitan.com/rss/all.xml/",
    # Fashion
    "WWD Fashion":      "https://wwd.com/feed/",
    "Highsnobiety":     "https://www.highsnobiety.com/feed/",
    "Hypebeast":        "https://hypebeast.com/feed",
    "Refinery29":       "https://www.refinery29.com/rss.xml",
    # Entertainment / Hollywood
    "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Variety":          "https://variety.com/feed/",
    "Entertainment Weekly": "https://feeds.feedburner.com/ew/news",
    "People Magazine":  "https://people.com/feed/",
    "E! News":          "https://www.eonline.com/news/rss",
    "TMZ":              "https://www.tmz.com/rss.xml",
    # Music
    "Billboard":        "https://www.billboard.com/feed/",
    # Pop Culture & Viral
    "BuzzFeed":         "https://www.buzzfeed.com/index.xml",
    "The Cut":          "https://www.thecut.com/rss/index.xml",
    "Vox":              "https://www.vox.com/rss/index.xml",
    "Complex":          "https://www.complex.com/rss",
    "Yahoo Entertainment": "https://www.yahoo.com/entertainment/rss",
    # Equestrian
    "Horse & Hound":    "https://www.horseandhound.co.uk/feed",
    "Chronicle of the Horse": "https://www.chronofhorse.com/feed",
}

TREND_KEYWORDS = [
    # Viral signals
    "viral", "trending", "everyone is", "people are", "tiktok made",
    "sold out", "obsessed", "can't stop", "blew up", "went viral",
    "breaking the internet", "everywhere right now",
    # Product virality
    "must-have", "sold out", "waitlist", "dupes", "dupe",
    "new drop", "limited edition", "collab", "collaboration",
    "tiktok made me buy", "viral product",
    # Beauty / body care
    "beauty secret", "skin trend", "hair trend", "body care",
    "skincare routine", "glow up", "beauty hack",
    # Fashion
    "aesthetic", "it girl", "style moment", "celebrity wore",
    "star wore", "red carpet", "outfit", "quiet luxury",
    # Pop culture
    "moment", "cultural reset", "iconic", "stan", "fandom",
    "celebrity news", "drama", "feud", "collab",
    # Equestrian
    "equestrian", "horse", "derby", "polo", "riding",
]

VIRAL_SIGNALS = [
    "went viral", "blew up", "trending on tiktok", "trending on x",
    "breaking the internet", "everyone is talking", "sold out instantly",
    "tiktok made me", "viral moment", "internet is obsessed",
]


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _is_trend_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in TREND_KEYWORDS)


def _is_viral(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(sig in combined for sig in VIRAL_SIGNALS)


def collect() -> dict[str, Any]:
    """Fetch articles from beauty, fashion, pop-culture, and equestrian RSS feeds."""
    results: dict[str, Any] = {
        "source": "News & Media",
        "articles": [],
        "viral_articles": [],
        "by_outlet": {},
        "top_topics": [],
        "errors": [],
    }

    try:
        import feedparser

        for outlet, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                outlet_articles = []

                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    summary = _clean_html(entry.get("summary", entry.get("description", "")))
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    tags = [t.term for t in entry.get("tags", [])[:5]]

                    article = {
                        "outlet": outlet,
                        "title": title,
                        "summary": summary[:300],
                        "url": link,
                        "published": published,
                        "tags": tags,
                        "trend_relevant": _is_trend_relevant(title, summary),
                        "is_viral": _is_viral(title, summary),
                    }
                    outlet_articles.append(article)
                    results["articles"].append(article)
                    if article["is_viral"]:
                        results["viral_articles"].append(article)

                results["by_outlet"][outlet] = outlet_articles

            except Exception as e:
                results["errors"].append(f"{outlet}: {e}")

        # Frequency-rank topics from titles
        word_freq: dict[str, int] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "to", "of",
            "and", "or", "in", "on", "at", "for", "with", "by", "from",
            "this", "that", "it", "how", "why", "what", "when", "who",
            "your", "her", "his", "their", "our", "more", "new", "best",
        }
        for article in results["articles"]:
            for word in article["title"].lower().split():
                word = re.sub(r"[^a-z]", "", word)
                if word and word not in stop_words and len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1

        results["top_topics"] = sorted(
            [{"topic": k, "mentions": v} for k, v in word_freq.items() if v > 1],
            key=lambda x: x["mentions"],
            reverse=True,
        )[:30]

        # Put trend-relevant articles first
        trend_articles = [a for a in results["articles"] if a["trend_relevant"]]
        other_articles = [a for a in results["articles"] if not a["trend_relevant"]]
        results["articles"] = trend_articles + other_articles

    except ImportError:
        results["errors"].append("feedparser not installed")
    except Exception as e:
        results["errors"].append(f"news general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(
        f"News: {len(results['articles'])} articles, "
        f"{len(results['viral_articles'])} viral signals, "
        f"from {len(results['by_outlet'])} outlets"
    )
    return results
