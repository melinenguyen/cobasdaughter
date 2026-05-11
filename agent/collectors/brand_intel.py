"""
Brand intelligence collector — tracks luxury brand activity, product launches,
and competitor moves via RSS feeds, no API keys required.
"""

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Feeds focused on brand news, product launches, and luxury market moves
BRAND_FEEDS = {
    # Industry trade — what brands are actually doing
    "Business of Fashion":    "https://www.businessoffashion.com/feed/",
    "Vogue Business":         "https://www.voguebusiness.com/rss",
    "Fashionista":            "https://fashionista.com/rss.xml",
    "Glossy":                 "https://www.glossy.co/feed/",
    "Beauty Independent":     "https://www.beautyindependent.com/feed/",
    "WWD Beauty":             "https://wwd.com/beauty-industry-news/feed/",
    "Cosmetics Design":       "https://www.cosmeticsdesign.com/rss/feed",
    "Cosmetics Business":     "https://cosmeticsbusiness.com/rss.xml",
    # PR / Brand releases
    "PR Newswire Beauty":     "https://www.prnewswire.com/rss/news-releases-list.rss?tagids=4816",
    "Business Wire Beauty":   "https://feed.businesswire.com/rss/home/?rss=G22",
    # Luxury market
    "Luxury Daily":           "https://www.luxurydaily.com/feed/",
    "The Zoe Report":         "https://www.thezoereport.com/rss",
    "Who What Wear":          "https://www.whowhatwear.com/rss",
    "Harper's Bazaar":        "https://www.harpersbazaar.com/rss/all.xml/",
    "InStyle":                "https://www.instyle.com/rss/all.xml",
    "Grazia":                 "https://graziamagazine.com/us/feed/",
    # Celebrity beauty
    "Byrdie":                 "https://www.byrdie.com/news-rss",
    "Into The Gloss":         "https://intothegloss.com/feed/",
}

# Luxury and beauty brands to track — CoBa's Daughter competitive + aspirational set
TRACKED_BRANDS = [
    # Ultra-luxury fashion
    "Hermès", "Hermes", "Chanel", "Dior", "Louis Vuitton", "Gucci", "Prada",
    "Bottega Veneta", "Valentino", "Balenciaga", "Givenchy", "Celine", "Loewe",
    "Miu Miu", "Jacquemus", "The Row",
    # Luxury beauty
    "La Mer", "La Prairie", "Sisley", "Augustinus Bader", "Vintner's Daughter",
    "Charlotte Tilbury", "Tom Ford Beauty", "YSL Beauty", "Giorgio Armani Beauty",
    "Dior Beauty", "Chanel Beauty", "NARS", "Clé de Peau",
    # Prestige / high-growth beauty
    "Drunk Elephant", "Summer Fridays", "Tatcha", "SK-II", "Glow Recipe",
    "Rhode", "Rare Beauty", "Fenty Beauty", "Tower 28", "ILIA",
    "Alo", "Lululemon",
    # Equestrian lifestyle
    "Ariat", "Pikeur", "Schoffel", "Parlanti", "Pessoa", "Kingsland",
    "Holland Cooper", "R.M. Williams",
    # Wellness / body care crossover
    "Goop", "Aesop", "Nécessaire", "Sol de Janeiro", "Vacation", "Supergoop",
]

# Launch / campaign signals — things we really want to catch
LAUNCH_SIGNALS = [
    "launch", "launches", "launched", "launching",
    "new collection", "new drop", "new release", "just dropped",
    "debuts", "debut", "introduces", "unveils", "unveiled",
    "collaborat", "collab", "x ", " x ",
    "limited edition", "limited-edition", "exclusive",
    "campaign", "ambassador", "partnership",
    "sold out", "selling out", "waitlist",
    "pop-up", "popup", "event",
    "fragrance", "skincare line", "body care line",
]

COMPETITOR_SIGNALS = [
    "luxury brand", "beauty brand", "fashion house", "designer brand",
    "high-end", "prestige beauty", "luxury market", "premium brand",
]


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _score_article(title: str, summary: str) -> dict[str, Any]:
    combined = (title + " " + summary).lower()
    brands_mentioned = [b for b in TRACKED_BRANDS if b.lower() in combined]
    is_launch = any(sig in combined for sig in LAUNCH_SIGNALS)
    is_competitor = any(sig in combined for sig in COMPETITOR_SIGNALS)
    relevance = len(brands_mentioned) * 3 + (5 if is_launch else 0) + (2 if is_competitor else 0)
    return {
        "brands_mentioned": brands_mentioned,
        "is_launch": is_launch,
        "is_competitor_move": is_competitor,
        "relevance_score": relevance,
    }


def collect() -> dict[str, Any]:
    """Fetch brand intelligence: luxury brand moves, product launches, competitor activity."""
    results: dict[str, Any] = {
        "source": "Brand Intelligence",
        "brand_launches": [],       # confirmed product/collection launches
        "brand_moves": [],          # campaigns, collabs, ambassador news
        "luxury_market_news": [],   # broader luxury/prestige market signals
        "tracked_brand_mentions": {},  # per-brand mention count
        "top_brand_topics": [],
        "errors": [],
    }

    for brand in TRACKED_BRANDS:
        results["tracked_brand_mentions"][brand] = 0

    try:
        import feedparser

        all_articles = []

        for outlet, feed_url in BRAND_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "")
                    summary = _clean_html(entry.get("summary", entry.get("description", "")))
                    link = entry.get("link", "")
                    published = entry.get("published", "")

                    scored = _score_article(title, summary)

                    article = {
                        "outlet": outlet,
                        "title": title,
                        "summary": summary[:400],
                        "url": link,
                        "published": published,
                        **scored,
                    }
                    all_articles.append(article)

                    # Track brand mentions
                    for brand in scored["brands_mentioned"]:
                        results["tracked_brand_mentions"][brand] = (
                            results["tracked_brand_mentions"].get(brand, 0) + 1
                        )

            except Exception as e:
                results["errors"].append(f"{outlet}: {e}")

        # Sort by relevance
        all_articles.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Bucket into categories
        for art in all_articles:
            if art["is_launch"] and art["relevance_score"] >= 5:
                results["brand_launches"].append(art)
            elif art["brands_mentioned"] or art["is_launch"]:
                results["brand_moves"].append(art)
            elif art["is_competitor_move"]:
                results["luxury_market_news"].append(art)

        # Limit sizes
        results["brand_launches"] = results["brand_launches"][:20]
        results["brand_moves"] = results["brand_moves"][:30]
        results["luxury_market_news"] = results["luxury_market_news"][:20]

        # Top brand mentions
        results["top_brand_topics"] = sorted(
            [{"brand": k, "mentions": v} for k, v in results["tracked_brand_mentions"].items() if v > 0],
            key=lambda x: x["mentions"],
            reverse=True,
        )[:15]

    except ImportError:
        results["errors"].append("feedparser not installed")
    except Exception as e:
        results["errors"].append(f"brand_intel general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(
        f"Brand Intel: {len(results['brand_launches'])} launches, "
        f"{len(results['brand_moves'])} brand moves, "
        f"{len(results['top_brand_topics'])} brands tracked"
    )
    return results
