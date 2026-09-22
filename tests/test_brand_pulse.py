from datetime import date

from agent.brand_pulse import PulseStore, import_keyword_metrics_csv


def mention(external_id, platform, published_at, sentiment="neutral", reach=0, engagement=0):
    return {
        "external_key": f"{platform}:{external_id}",
        "platform": platform,
        "external_id": external_id,
        "source_url": f"https://example.test/{external_id}",
        "title": "CoBa's Daughter is lovely",
        "published_at": published_at,
        "matched_term": "CoBa's Daughter",
        "estimated_reach": reach,
        "engagement_count": engagement,
        "sentiment": sentiment,
        "sentiment_confidence": .8,
    }


def test_store_aggregates_mentions_and_search_metrics():
    store = PulseStore("sqlite:///:memory:")
    store.upsert_mention(mention("one", "reddit", "2026-09-20T10:00:00Z", "positive", 200, 12))
    store.upsert_mention(mention("two", "reddit", "2026-09-20T12:00:00Z", "negative", 100, 7))
    store.upsert_mention(mention("three", "instagram", "2026-09-21T12:00:00Z", "positive", 300, 20))
    store.commit()
    store.refresh_mention_metrics(date(2026, 9, 20), date(2026, 9, 21))
    store.upsert_metric(date(2026, 9, 20), "google", "brand_search_impressions", 44)
    store.upsert_metric(date(2026, 9, 21), "google", "brand_search_impressions", 56)
    store.commit()

    totals = store.aggregate(date(2026, 9, 20), date(2026, 9, 21), ["google", "reddit", "instagram"])
    assert totals["mentions"] == 3
    assert totals["reach"] == 600
    assert totals["engagement"] == 39
    assert totals["search_interest"] is None
    assert totals["search_impressions"] == 100
    assert round(totals["positive_share"], 1) == 66.7

    trend = store.trend(date(2026, 9, 20), date(2026, 9, 21), ["google", "reddit", "instagram"])
    assert trend == [
        {"date": "2026-09-20", "mentions": 2, "search_interest": 0},
        {"date": "2026-09-21", "mentions": 1, "search_interest": 0},
    ]
    store.close()


def test_keyword_csv_import_is_upsertable():
    store = PulseStore("sqlite:///:memory:")
    source = "date,metric_name,metric_value\n2026-09-01,brand_search_interest,52\n2026-09-02,brand_search_interest,61\n"
    assert import_keyword_metrics_csv(store, source) == 2
    totals = store.aggregate(date(2026, 9, 1), date(2026, 9, 2), ["google"])
    assert totals["search_interest"] == 56.5
    store.close()
