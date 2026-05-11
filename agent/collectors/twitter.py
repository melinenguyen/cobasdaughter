import logging
import requests
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    # Real-time beauty & skincare virality
    "#trending #beauty",
    "#viral #skincare OR #viral #bodycare",
    "#GRWM OR #skincareroutine",
    "#viral #makeup OR #makeuptrend",
    "#beautytok OR #skintok",
    # Brand launches & drops — catch the moment they happen
    "beauty launch OR beauty drop OR beauty collab",
    "new collection fashion OR new drop luxury",
    "limited edition beauty OR sold out beauty",
    "brand collab OR designer collab",
    # Hollywood & celebrity culture — immediate
    "#celebrity #beauty OR #celebstyle",
    "#redcarpet OR #METgala OR #Oscars OR #Grammys",
    "celebrity wore OR spotted wearing OR street style",
    "celebrity brand OR celebrity beauty line",
    # Pop culture & viral moments
    "#tiktoktrend OR #tiktokmademebuyit",
    "#viral #fashion OR #viral #luxury",
    "#OOTD OR #aesthetics",
    "#popculture OR #culturalmoment",
    # Equestrian crossover
    "#equestrian OR #horsegirl OR #equestrianstyle",
    "#equestrian #beauty OR #equestrian #fashion",
    # Luxury & high-end tracking
    "#quietluxury OR #oldmoney OR #stealthwealth",
    "#luxuryfashion OR #luxurybeauty OR #designerbrand",
]

WOEID_US = 23424977  # Yahoo! Where On Earth ID for United States


def collect(bearer_token: str) -> dict[str, Any]:
    """Collect trending tweets and hashtags via Twitter/X API v2."""
    results: dict[str, Any] = {
        "source": "Twitter/X",
        "trending_hashtags": [],
        "trending_tweets": [],
        "errors": [],
    }

    if not bearer_token:
        results["errors"].append("Twitter bearer token not configured")
        results["collected_at"] = datetime.utcnow().isoformat()
        return results

    headers = {"Authorization": f"Bearer {bearer_token}"}

    # Fetch recent tweets for each query
    for query in SEARCH_QUERIES:
        try:
            params = {
                "query": f"{query} lang:en -is:retweet",
                "max_results": 10,
                "tweet.fields": "public_metrics,created_at,text,author_id",
                "sort_order": "relevancy",
            }
            resp = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    results["trending_tweets"].append({
                        "text": tweet["text"],
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "impressions": metrics.get("impression_count", 0),
                        "query": query,
                        "created_at": tweet.get("created_at", ""),
                    })
            elif resp.status_code == 429:
                results["errors"].append(f"Rate limited for query: {query}")
            else:
                results["errors"].append(f"API {resp.status_code} for query: {query}")

        except Exception as e:
            results["errors"].append(f"tweet search [{query}]: {e}")

    # Extract hashtags from tweets
    hashtag_counts: dict[str, int] = {}
    for tweet in results["trending_tweets"]:
        words = tweet["text"].split()
        for word in words:
            if word.startswith("#") and len(word) > 2:
                tag = word.lower().rstrip(".,!?")
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1

    results["trending_hashtags"] = sorted(
        [{"hashtag": k, "count": v} for k, v in hashtag_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:50]

    # Sort tweets by engagement
    results["trending_tweets"].sort(
        key=lambda x: x["likes"] + x["retweets"] * 3,
        reverse=True,
    )

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(f"Twitter: {len(results['trending_tweets'])} tweets, {len(results['trending_hashtags'])} hashtags")
    return results
