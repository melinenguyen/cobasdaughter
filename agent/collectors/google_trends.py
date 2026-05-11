import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def collect() -> dict[str, Any]:
    """Fetch Google Trends data: daily trending searches + keyword interest."""
    results: dict[str, Any] = {
        "source": "Google Trends",
        "daily_trending": [],
        "keyword_interest": {},
        "rising_queries": {},
        "errors": [],
    }

    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="en-US", tz=300, timeout=(10, 25), retries=2, backoff_factor=0.5)

        # 1. Daily trending searches (US)
        try:
            daily_df = pt.trending_searches(pn="united_states")
            if daily_df is not None and not daily_df.empty:
                results["daily_trending"] = daily_df[0].tolist()[:30]
        except Exception as e:
            results["errors"].append(f"daily trending: {e}")

        # 2. Real-time trending searches
        try:
            rt = pt.realtime_trending_searches(pn="US")
            if rt is not None and not rt.empty:
                for _, row in rt.head(20).iterrows():
                    title = row.get("title", "")
                    if title and title not in results["daily_trending"]:
                        results["daily_trending"].append(title)
        except Exception as e:
            results["errors"].append(f"realtime trending: {e}")

        # 3. Interest over time for category seeds
        category_seeds = [
            # Beauty & body care
            ["beauty trend", "skincare trend", "body care routine"],
            ["viral beauty product", "sold out skincare", "beauty launch"],
            # Fashion & luxury
            ["fashion trend", "quiet luxury", "old money aesthetic"],
            ["luxury brand", "designer collab", "new collection"],
            # Hollywood & celebrity
            ["celebrity news", "celebrity beauty", "red carpet style"],
            ["celebrity brand", "celebrity collab", "celebrity wore"],
            # Viral & pop culture
            ["tiktok trend", "viral product", "tiktok made me buy"],
            ["pop culture moment", "viral moment", "trending now"],
            # Equestrian crossover
            ["equestrian fashion", "horse girl aesthetic", "equestrian style"],
        ]

        for seeds in category_seeds:
            try:
                pt.build_payload(seeds[:5], cat=0, timeframe="now 7-d", geo="US")
                interest_df = pt.interest_over_time()
                if interest_df is not None and not interest_df.empty:
                    avg = interest_df.drop(columns=["isPartial"], errors="ignore").mean()
                    for kw in seeds:
                        if kw in avg.index:
                            results["keyword_interest"][kw] = round(float(avg[kw]), 1)

                # Rising queries
                related = pt.related_queries()
                for kw in seeds:
                    if kw in related and related[kw].get("rising") is not None:
                        rising_df = related[kw]["rising"]
                        if rising_df is not None and not rising_df.empty:
                            results["rising_queries"][kw] = rising_df.head(5).to_dict("records")
            except Exception as e:
                results["errors"].append(f"interest [{seeds[0]}]: {e}")

    except ImportError:
        results["errors"].append("pytrends not installed")
    except Exception as e:
        results["errors"].append(f"google trends general: {e}")

    results["collected_at"] = datetime.utcnow().isoformat()
    logger.info(f"Google Trends: {len(results['daily_trending'])} trending, {len(results['keyword_interest'])} keywords")
    return results
