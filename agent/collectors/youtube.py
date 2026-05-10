import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

CATEGORY_IDS = {
    "0": "All",
    "10": "Music",
    "23": "Comedy",
    "24": "Entertainment",
    "26": "How-to & Style",
    "27": "Education",
}


def collect(api_key: str) -> dict[str, Any]:
    """Collect YouTube trending videos in the US."""
    results: dict[str, Any] = {
        "source": "YouTube",
        "trending_videos": [],
        "by_category": {},
        "top_channels": [],
        "errors": [],
    }

    if not api_key:
        results["errors"].append("YouTube API key not configured")
        results["collected_at"] = datetime.utcnow().isoformat()
        return results

    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)

        for cat_id, cat_name in CATEGORY_IDS.items():
            try:
                request = youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    chart="mostPopular",
                    regionCode="US",
                    videoCategoryId=cat_id if cat_id != "0" else None,
                    maxResults=10,
                    hl="en",
                )
                response = request.execute()

                cat_videos = []
                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    video = {
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "category": cat_name,
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "tags": snippet.get("tags", [])[:10],
                        "description_snippet": snippet.get("description", "")[:200],
                        "video_id": item["id"],
                        "url": f"https://youtube.com/watch?v={item['id']}",
                        "published_at": snippet.get("publishedAt", ""),
                    }
                    cat_videos.append(video)
                    results["trending_videos"].append(video)

                results["by_category"][cat_name] = cat_videos

            except Exception as e:
                results["errors"].append(f"YouTube cat {cat_name}: {e}")

        # Top channels
        channel_counts: dict[str, int] = {}
        for v in results["trending_videos"]:
            ch = v["channel"]
            channel_counts[ch] = channel_counts.get(ch, 0) + 1
        results["top_channels"] = sorted(
            [{"channel": k, "trending_videos": v} for k, v in channel_counts.items()],
            key=lambda x: x["trending_videos"],
            reverse=True,
        )[:10]

        results["trending_videos"].sort(key=lambda x: x["views"], reverse=True)

    except ImportError:
        results["errors"].append("google-api-python-client not installed")
    except Exception as e:
        results["errors"].append(f"youtube general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(f"YouTube: {len(results['trending_videos'])} trending videos")
    return results
