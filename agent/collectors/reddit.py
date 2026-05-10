import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "popculture", "entertainment", "beauty", "SkincareAddiction",
    "MakeupAddiction", "femalefashionadvice", "malefashionadvice",
    "streetwear", "TikTokCringe", "TikTok", "Music", "movies",
    "television", "celebrity", "Trending", "BeautyGuruChatter",
    "HollywoodGossip", "fragrance", "Sneakers", "FashionReps",
]


def collect(client_id: str, client_secret: str, user_agent: str) -> dict[str, Any]:
    """Collect hot/rising posts from US pop-culture subreddits."""
    results: dict[str, Any] = {
        "source": "Reddit",
        "hot_posts": [],
        "rising_posts": [],
        "subreddit_summary": {},
        "errors": [],
    }

    if not client_id or not client_secret:
        results["errors"].append("Reddit credentials not configured")
        results["collected_at"] = datetime.utcnow().isoformat()
        return results

    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        for sub_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(sub_name)
                hot = []
                for post in subreddit.hot(limit=10):
                    if post.stickied:
                        continue
                    item = {
                        "subreddit": sub_name,
                        "title": post.title,
                        "score": post.score,
                        "upvote_ratio": post.upvote_ratio,
                        "num_comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                        "flair": post.link_flair_text,
                        "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat(),
                    }
                    hot.append(item)
                    results["hot_posts"].append(item)

                results["subreddit_summary"][sub_name] = {
                    "top_post": hot[0]["title"] if hot else None,
                    "avg_score": round(sum(p["score"] for p in hot) / len(hot), 0) if hot else 0,
                }

                # Rising
                for post in subreddit.rising(limit=5):
                    if post.stickied:
                        continue
                    results["rising_posts"].append({
                        "subreddit": sub_name,
                        "title": post.title,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                    })

            except Exception as e:
                results["errors"].append(f"r/{sub_name}: {e}")

        # Sort by engagement
        results["hot_posts"].sort(key=lambda x: x["score"] * x["upvote_ratio"], reverse=True)
        results["rising_posts"].sort(key=lambda x: x["score"], reverse=True)

    except ImportError:
        results["errors"].append("praw not installed")
    except Exception as e:
        results["errors"].append(f"reddit general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(f"Reddit: {len(results['hot_posts'])} hot, {len(results['rising_posts'])} rising")
    return results
