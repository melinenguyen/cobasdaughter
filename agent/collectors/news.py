import logging
import re
import requests
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "Entertainment Weekly": "https://feeds.feedburner.com/ew/news",
    "People Magazine": "https://people.com/feed/",
    "E! News": "https://www.eonline.com/news/rss",
    "Cosmopolitan": "https://www.cosmopolitan.com/rss/all.xml/",
    "Refinery29": "https://www.refinery29.com/rss.xml",
    "Hypebeast": "https://hypebeast.com/feed",
    "Byrdie Beauty": "https://www.byrdie.com/news-rss",
    "Allure": "https://www.allure.com/feed/rss",
    "WWD Fashion": "https://wwd.com/feed/",
    "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Variety": "https://variety.com/feed/",
    "Billboard": "https://www.billboard.com/feed/",
    "Complex": "https://www.complex.com/rss",
    "Highsnobiety": "https://www.highsnobiety.com/feed/",
}

TREND_KEYWORDS = [
    "trend", "viral", "trending", "hot", "popular", "must-have",
    "everyone is", "people are", "beauty secret", "aesthetic",
    "it girl", "celebrity style", "star wore", "new drop",
    "sold out", "obsessed", "tiktok made me buy", "dupes",
    "collaboration", "collab", "limited edition",
]


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _is_trend_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in TREND_KEYWORDS)


def collect() -> dict[str, Any]:
    """Fetch articles from beauty, fashion, and entertainment RSS feeds."""
    results: dict[str, Any] = {
        "source": "News & Media",
        "articles": [],
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
                    }
                    outlet_articles.append(article)
                    results["articles"].append(article)

                results["by_outlet"][outlet] = outlet_articles

            except Exception as e:
                results["errors"].append(f"{outlet}: {e}")

        # Frequency-rank topics from titles
        word_freq: dict[str, int] = {}
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "of",
                      "and", "or", "in", "on", "at", "for", "with", "by", "from",
                      "this", "that", "it", "how", "why", "what", "when", "who"}
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

        # Filter trend-relevant articles to top
        trend_articles = [a for a in results["articles"] if a["trend_relevant"]]
        other_articles = [a for a in results["articles"] if not a["trend_relevant"]]
        results["articles"] = trend_articles + other_articles

    except ImportError:
        results["errors"].append("feedparser not installed")
    except Exception as e:
        results["errors"].append(f"news general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(f"News: {len(results['articles'])} articles from {len(results['by_outlet'])} outlets")
    return results
