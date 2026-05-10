"""
Instagram Graph API collector.

Fetches trending hashtag data using the Instagram Graph API.
Requires a Facebook App with Instagram Basic Display or Graph API access,
connected to an Instagram Business or Creator account.

Required env vars:
  INSTAGRAM_ACCESS_TOKEN      — long-lived user access token
  INSTAGRAM_BUSINESS_ACCOUNT_ID — your IG business account numeric ID
"""

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"

TREND_HASHTAGS = [
    "beauty", "skincare", "bodycare", "selfcare", "fashion", "ootd",
    "equestrian", "horses", "equestrianstyle", "ridinglife", "horsegirl",
    "trendingbeauty", "viralbeauty", "aesthetics", "popculture",
    "hollywoodstyle", "streetstyle", "luxuryfashion", "wellness",
]


def _get_hashtag_id(session: requests.Session, account_id: str, hashtag: str) -> str | None:
    """Resolve a hashtag string to its Graph API ID."""
    resp = session.get(
        f"{GRAPH_BASE}/ig_hashtag_search",
        params={"user_id": account_id, "q": hashtag},
    )
    data = resp.json()
    items = data.get("data", [])
    return items[0]["id"] if items else None


def _get_hashtag_media(
    session: requests.Session,
    account_id: str,
    hashtag_id: str,
    edge: str = "top_media",
) -> list[dict]:
    """Fetch top or recent media for a hashtag ID."""
    resp = session.get(
        f"{GRAPH_BASE}/{hashtag_id}/{edge}",
        params={
            "user_id": account_id,
            "fields": "id,media_type,like_count,comments_count,timestamp,caption",
        },
    )
    return resp.json().get("data", [])


def collect(access_token: str, account_id: str) -> dict[str, Any]:
    """Collect trending hashtag signals from Instagram Graph API."""
    results: dict[str, Any] = {
        "source": "Instagram",
        "trending_hashtags": [],
        "top_media": [],
        "errors": [],
    }

    if not access_token or not account_id:
        results["errors"].append("Instagram credentials not configured")
        results["collected_at"] = datetime.utcnow().isoformat()
        return results

    session = requests.Session()
    session.params = {"access_token": access_token}  # type: ignore[assignment]

    for tag in TREND_HASHTAGS:
        try:
            hashtag_id = _get_hashtag_id(session, account_id, tag)
            if not hashtag_id:
                continue

            media_items = _get_hashtag_media(session, account_id, hashtag_id, "top_media")

            total_likes = sum(m.get("like_count", 0) for m in media_items)
            total_comments = sum(m.get("comments_count", 0) for m in media_items)
            post_count = len(media_items)

            signal = "Rising"
            if total_likes > 50000:
                signal = "Viral"
            elif total_likes > 10000:
                signal = "High"

            results["trending_hashtags"].append({
                "hashtag": f"#{tag}",
                "posts_sampled": post_count,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "signal": signal,
            })

            for item in media_items[:3]:
                caption = (item.get("caption") or "")[:200]
                results["top_media"].append({
                    "hashtag": f"#{tag}",
                    "media_type": item.get("media_type"),
                    "likes": item.get("like_count", 0),
                    "comments": item.get("comments_count", 0),
                    "caption_snippet": caption,
                    "timestamp": item.get("timestamp", ""),
                })

        except Exception as e:
            results["errors"].append(f"#{tag}: {e}")

    results["trending_hashtags"].sort(key=lambda x: x["total_likes"], reverse=True)
    results["top_media"].sort(key=lambda x: x["likes"], reverse=True)
    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(
        f"Instagram: {len(results['trending_hashtags'])} hashtags, "
        f"{len(results['top_media'])} media items"
    )
    return results
