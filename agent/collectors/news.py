import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    # Beauty & Skincare
    "Allure":               "https://www.allure.com/feed/rss",
    "Byrdie Beauty":        "https://www.byrdie.com/news-rss",
    "Cosmopolitan":         "https://www.cosmopolitan.com/rss/all.xml/",
    "Glamour":              "https://www.glamour.com/feed/rss",
    "Marie Claire":         "https://www.marieclaire.com/rss/all.xml/",
    # Fashion
    "WWD Fashion":          "https://wwd.com/feed/",
    "Highsnobiety":         "https://www.highsnobiety.com/feed/",
    "Hypebeast":            "https://hypebeast.com/feed",
    "Refinery29":           "https://www.refinery29.com/rss.xml",
    "Who What Wear":        "https://www.whowhatwear.com/rss",
    "The Zoe Report":       "https://www.thezoereport.com/rss",
    # Entertainment / Hollywood — aggressive celebrity tracking
    "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Variety":              "https://variety.com/feed/",
    "Deadline":             "https://deadline.com/feed/",
    "Entertainment Weekly": "https://feeds.feedburner.com/ew/news",
    "People Magazine":      "https://people.com/feed/",
    "E! News":              "https://www.eonline.com/news/rss",
    "TMZ":                  "https://www.tmz.com/rss.xml",
    "Page Six":             "https://pagesix.com/feed/",
    "Just Jared":           "https://www.justjared.com/feed/",
    "Us Weekly":            "https://www.usmagazine.com/feed/",
    "Daily Mail Showbiz":   "https://www.dailymail.co.uk/tvshowbiz/index.rss",
    "InStyle":              "https://www.instyle.com/rss/all.xml",
    "Harper's Bazaar":      "https://www.harpersbazaar.com/rss/all.xml/",
    # Music
    "Billboard":            "https://www.billboard.com/feed/",
    "Rolling Stone":        "https://www.rollingstone.com/feed/",
    "Pitchfork":            "https://pitchfork.com/rss/news/",
    # Pop Culture & Viral
    "BuzzFeed":             "https://www.buzzfeed.com/index.xml",
    "The Cut":              "https://www.thecut.com/rss/index.xml",
    "Vox":                  "https://www.vox.com/rss/index.xml",
    "Complex":              "https://www.complex.com/rss",
    "Yahoo Entertainment":  "https://www.yahoo.com/entertainment/rss",
    "PopSugar":             "https://www.popsugar.com/feeds/latest",
    "Seventeen":            "https://www.seventeen.com/rss/all.xml/",
    # Luxury & Brand Intelligence
    "Business of Fashion":  "https://www.businessoffashion.com/feed/",
    "Vogue Business":       "https://www.voguebusiness.com/rss",
    "Fashionista":          "https://fashionista.com/rss.xml",
    "Glossy":               "https://www.glossy.co/feed/",
    "Luxury Daily":         "https://www.luxurydaily.com/feed/",
    # Equestrian
    "Horse & Hound":        "https://www.horseandhound.co.uk/feed",
    "Chronicle of the Horse": "https://www.chronofhorse.com/feed",
}

TREND_KEYWORDS = [
    # Viral signals
    "viral", "trending", "everyone is", "people are", "tiktok made",
    "sold out", "obsessed", "can't stop", "blew up", "went viral",
    "breaking the internet", "everywhere right now", "internet obsessed",
    # Product / brand launches
    "launches", "launched", "just dropped", "new drop", "new release",
    "limited edition", "collab", "collaboration", "new collection",
    "debuts", "unveils", "introducing", "just launched",
    "waitlist", "sold out in", "restocked",
    "must-have", "dupe", "tiktok made me buy", "viral product",
    # Celebrity / Hollywood
    "celebrity wore", "star wore", "red carpet", "spotted wearing",
    "celebrity beauty", "celebrity brand", "celebrity collab",
    "celebrity launches", "founded by", "actor wore", "singer wore",
    # Beauty / body care
    "beauty secret", "skin trend", "hair trend", "body care",
    "skincare routine", "glow up", "beauty hack", "it product",
    # Fashion / luxury
    "aesthetic", "it girl", "style moment", "quiet luxury",
    "old money", "stealth wealth", "capsule wardrobe",
    "designer", "luxury brand", "high-end", "prestige",
    # Pop culture
    "moment", "cultural reset", "iconic", "stan", "fandom",
    "celebrity news", "drama", "feud", "era", "girlhood",
    # Equestrian
    "equestrian", "horse", "derby", "polo", "riding", "horse girl",
]

VIRAL_SIGNALS = [
    "went viral", "blew up", "trending on tiktok", "trending on x",
    "breaking the internet", "everyone is talking", "sold out instantly",
    "tiktok made me", "viral moment", "internet is obsessed",
    "sold out in minutes", "sold out in hours", "crashed the site",
    "broke the internet", "everyone wants", "can't keep in stock",
    "fastest selling", "record breaking", "overnight sensation",
]

LAUNCH_SIGNALS = [
    "launch", "launches", "launched", "just dropped", "new drop",
    "new collection", "new release", "debuts", "unveils", "introduces",
    "limited edition", "collab", "collaboration", "partnership",
    "new fragrance", "new skincare", "new makeup", "new campaign",
]


FRESHNESS_HOURS = 8  # only surface articles published in last 8 hours


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_published(entry) -> datetime | None:
    """Try to extract a timezone-aware published datetime from a feedparser entry."""
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    if entry.get("updated_parsed"):
        try:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _is_fresh(entry, cutoff: datetime) -> bool:
    """Return True if the article was published after the cutoff, or if we can't tell."""
    pub = _parse_published(entry)
    if pub is None:
        return True  # unknown publish time — include it, better safe than sorry
    return pub >= cutoff


def _is_trend_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in TREND_KEYWORDS)


def _is_viral(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(sig in combined for sig in VIRAL_SIGNALS)


def _is_launch(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(sig in combined for sig in LAUNCH_SIGNALS)


def collect() -> dict[str, Any]:
    """Fetch articles from beauty, fashion, Hollywood, pop-culture, and equestrian RSS feeds."""
    results: dict[str, Any] = {
        "source": "News & Media",
        "articles": [],
        "viral_articles": [],
        "launch_articles": [],
        "hollywood_articles": [],
        "by_outlet": {},
        "top_topics": [],
        "errors": [],
    }

    HOLLYWOOD_OUTLETS = {
        "The Hollywood Reporter", "Variety", "Deadline", "Entertainment Weekly",
        "People Magazine", "E! News", "TMZ", "Page Six", "Just Jared",
        "Us Weekly", "Daily Mail Showbiz",
    }

    try:
        import feedparser

        cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_HOURS)

        for outlet, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                outlet_articles = []

                for entry in feed.entries[:25]:  # scan more, filter by freshness
                    if not _is_fresh(entry, cutoff):
                        continue

                    title = entry.get("title", "")
                    summary = _clean_html(entry.get("summary", entry.get("description", "")))
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    tags = [t.term for t in entry.get("tags", [])[:5]]
                    pub_dt = _parse_published(entry)
                    hours_ago = (
                        round((datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600, 1)
                        if pub_dt else None
                    )

                    article = {
                        "outlet": outlet,
                        "title": title,
                        "summary": summary[:300],
                        "url": link,
                        "published": published,
                        "hours_ago": hours_ago,
                        "tags": tags,
                        "trend_relevant": _is_trend_relevant(title, summary),
                        "is_viral": _is_viral(title, summary),
                        "is_launch": _is_launch(title, summary),
                        "is_hollywood": outlet in HOLLYWOOD_OUTLETS,
                    }
                    outlet_articles.append(article)
                    results["articles"].append(article)
                    if article["is_viral"]:
                        results["viral_articles"].append(article)
                    if article["is_launch"]:
                        results["launch_articles"].append(article)
                    if article["is_hollywood"]:
                        results["hollywood_articles"].append(article)

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
        f"{len(results['viral_articles'])} viral, "
        f"{len(results['launch_articles'])} launches, "
        f"{len(results['hollywood_articles'])} Hollywood, "
        f"from {len(results['by_outlet'])} outlets"
    )
    return results
