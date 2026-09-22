"""CoBa's Daughter Brand Pulse collector and aggregate-data store.

This module is deliberately separate from the existing trend-report agent. It
collects only approved, configured sources, stores data in a private database,
and exposes no provider credential to the dashboard.

Run locally:
    BRAND_PULSE_DATABASE_URL=sqlite:///data/brand_pulse.db python -m agent.brand_pulse

Run in production:
    BRAND_PULSE_DATABASE_URL=postgresql://... python -m agent.brand_pulse
"""

import base64
import csv
import io
import json
import logging
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)

DEFAULT_TERMS = ["CoBa's Daughter", "Coba's Daughter", "Co Ba's Daughter", "#cobasdaughter"]
MENTION_METRICS = ("mentions", "reach", "engagement", "positive_share")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_terms(raw: str = "") -> List[str]:
    terms = [term.strip() for term in raw.split(",") if term.strip()] if raw else DEFAULT_TERMS
    # Preserve order while removing accidental duplicates.
    return list(dict.fromkeys(terms))


def as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def parse_iso_datetime(value: Any) -> str:
    """Return a safe ISO timestamp, accepting the common source formats."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        text = str(value or "")
        if not text:
            return utc_now()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def sentiment_for(text: str) -> Tuple[str, float]:
    """A transparent fallback classifier; replace with a reviewed model later."""
    lowered = (text or "").lower()
    positive = ("love", "great", "beautiful", "favourite", "favorite", "amazing", "recommend", "perfect")
    negative = ("bad", "disappoint", "avoid", "terrible", "expensive", "hate", "poor")
    good = sum(word in lowered for word in positive)
    bad = sum(word in lowered for word in negative)
    if good > bad:
        return "positive", min(.92, .58 + good * .12)
    if bad > good:
        return "negative", min(.92, .58 + bad * .12)
    return "neutral", .52


class PulseStore:
    """Small SQL adapter supporting PostgreSQL in production and SQLite locally."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "BRAND_PULSE_DATABASE_URL", "sqlite:///data/brand_pulse.db"
        )
        self.is_postgres = self.database_url.startswith(("postgres://", "postgresql://"))
        if self.is_postgres:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:  # pragma: no cover - exercised in production
                raise RuntimeError("PostgreSQL support needs psycopg. Run pip install -r requirements.txt.") from exc
            self.connection = psycopg.connect(self.database_url, row_factory=dict_row)
        else:
            path = self.database_url
            if path.startswith("sqlite:///"):
                path = path[len("sqlite:///"):]
            db_path = Path(path)
            if str(db_path) != ":memory:":
                db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(db_path))
            self.connection.row_factory = sqlite3.Row
        self.create_schema()

    def _sql(self, statement: str) -> str:
        return statement.replace("?", "%s") if self.is_postgres else statement

    def execute(self, statement: str, values: Tuple[Any, ...] = ()):
        cursor = self.connection.cursor()
        cursor.execute(self._sql(statement), values)
        return cursor

    def fetchall(self, statement: str, values: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        cursor = self.execute(statement, values)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def create_schema(self) -> None:
        self.execute(
            """CREATE TABLE IF NOT EXISTS pulse_mentions (
                external_key TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                external_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                matched_term TEXT NOT NULL,
                engagement_count INTEGER NOT NULL DEFAULT 0,
                estimated_reach INTEGER NOT NULL DEFAULT 0,
                sentiment TEXT NOT NULL DEFAULT 'neutral',
                sentiment_confidence REAL NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )"""
        )
        self.execute(
            """CREATE TABLE IF NOT EXISTS pulse_daily_metrics (
                metric_date TEXT NOT NULL,
                platform TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                brand_term TEXT NOT NULL DEFAULT 'all',
                geography TEXT NOT NULL DEFAULT 'global',
                calculated_at TEXT NOT NULL,
                PRIMARY KEY (metric_date, platform, metric_name, brand_term, geography)
            )"""
        )
        self.execute(
            """CREATE TABLE IF NOT EXISTS pulse_sync_runs (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                records_written INTEGER NOT NULL DEFAULT 0,
                latest_available_at TEXT,
                detail TEXT NOT NULL DEFAULT ''
            )"""
        )
        self.commit()

    def upsert_mention(self, mention: Dict[str, Any]) -> None:
        payload = {
            "external_key": mention["external_key"],
            "platform": mention["platform"],
            "external_id": str(mention.get("external_id") or mention["external_key"]),
            "source_url": mention.get("source_url") or "",
            "title": (mention.get("title") or "")[:1000],
            "published_at": parse_iso_datetime(mention.get("published_at")),
            "collected_at": utc_now(),
            "matched_term": mention.get("matched_term") or "unknown",
            "engagement_count": int(mention.get("engagement_count") or 0),
            "estimated_reach": int(mention.get("estimated_reach") or 0),
            "sentiment": mention.get("sentiment") or "neutral",
            "sentiment_confidence": float(mention.get("sentiment_confidence") or 0),
            "metadata_json": json.dumps(mention.get("metadata") or {}, ensure_ascii=False),
        }
        columns = list(payload)
        insert_values = tuple(payload[column] for column in columns)
        assignments = ", ".join(
            f"{column}=excluded.{column}" for column in columns if column not in {"external_key", "collected_at"}
        )
        self.execute(
            f"INSERT INTO pulse_mentions ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)}) "
            f"ON CONFLICT(external_key) DO UPDATE SET {assignments}, collected_at=excluded.collected_at",
            insert_values,
        )

    def upsert_metric(
        self,
        metric_date: date,
        platform: str,
        metric_name: str,
        metric_value: float,
        brand_term: str = "all",
        geography: str = "global",
    ) -> None:
        self.execute(
            """INSERT INTO pulse_daily_metrics
            (metric_date, platform, metric_name, metric_value, brand_term, geography, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_date, platform, metric_name, brand_term, geography)
            DO UPDATE SET metric_value=excluded.metric_value, calculated_at=excluded.calculated_at""",
            (metric_date.isoformat(), platform, metric_name, float(metric_value), brand_term, geography, utc_now()),
        )

    def record_sync(
        self, platform: str, started_at: str, status: str, records_written: int, detail: str = "", latest_available_at: str = ""
    ) -> None:
        self.execute(
            """INSERT INTO pulse_sync_runs
            (id, platform, started_at, finished_at, status, records_written, latest_available_at, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), platform, started_at, utc_now(), status, records_written, latest_available_at or None, detail[:1500]),
        )
        self.commit()

    def refresh_mention_metrics(self, start: date, end: date, geography: str = "global") -> None:
        start_value, end_value = start.isoformat(), end.isoformat()
        placeholders = ", ".join("?" for _ in MENTION_METRICS)
        self.execute(
            f"DELETE FROM pulse_daily_metrics WHERE metric_name IN ({placeholders}) AND metric_date >= ? AND metric_date <= ?",
            tuple(MENTION_METRICS) + (start_value, end_value),
        )
        rows = self.fetchall(
            """SELECT substr(published_at, 1, 10) AS metric_date, platform,
                      COUNT(*) AS mentions,
                      COALESCE(SUM(estimated_reach), 0) AS reach,
                      COALESCE(SUM(engagement_count), 0) AS engagement,
                      AVG(CASE WHEN sentiment = 'positive' THEN 100.0 ELSE 0.0 END) AS positive_share
               FROM pulse_mentions
               WHERE substr(published_at, 1, 10) >= ? AND substr(published_at, 1, 10) <= ?
               GROUP BY substr(published_at, 1, 10), platform""",
            (start_value, end_value),
        )
        for row in rows:
            day = date.fromisoformat(row["metric_date"])
            for metric in MENTION_METRICS:
                self.upsert_metric(day, row["platform"], metric, row[metric] or 0, geography=geography)
        self.commit()

    def aggregate(self, start: date, end: date, platforms: Iterable[str]) -> Dict[str, float]:
        chosen = list(platforms)
        if not chosen:
            return {"search_interest": 0, "mentions": 0, "reach": 0, "engagement": 0, "positive_share": 0}
        marks = ", ".join("?" for _ in chosen)
        rows = self.fetchall(
            f"""SELECT metric_name,
                       CASE WHEN metric_name = 'brand_search_interest'
                            THEN AVG(metric_value) ELSE SUM(metric_value) END AS total
                FROM pulse_daily_metrics
                WHERE metric_date >= ? AND metric_date <= ? AND platform IN ({marks})
                GROUP BY metric_name""",
            (start.isoformat(), end.isoformat(), *chosen),
        )
        values = {row["metric_name"]: float(row["total"] or 0) for row in rows}
        positive_rows = self.fetchall(
            f"""SELECT AVG(CASE WHEN sentiment='positive' THEN 100.0 ELSE 0.0 END) AS total FROM pulse_mentions
                WHERE substr(published_at,1,10) >= ? AND substr(published_at,1,10) <= ? AND platform IN ({marks})""",
            (start.isoformat(), end.isoformat(), *chosen),
        )
        return {
            "search_interest": values.get("brand_search_interest"),
            "search_impressions": values.get("brand_search_impressions"),
            "mentions": values.get("mentions", 0),
            "reach": values.get("reach", 0),
            "engagement": values.get("engagement", 0),
            "positive_share": float(positive_rows[0]["total"] or 0) if positive_rows else 0,
        }

    def trend(self, start: date, end: date, platforms: Iterable[str]) -> List[Dict[str, Any]]:
        chosen = list(platforms)
        if not chosen:
            return []
        marks = ", ".join("?" for _ in chosen)
        rows = self.fetchall(
            f"""SELECT metric_date,
                       SUM(CASE WHEN metric_name='mentions' THEN metric_value ELSE 0 END) AS mentions,
                       AVG(CASE WHEN metric_name='brand_search_interest' THEN metric_value END) AS search_interest
                FROM pulse_daily_metrics
                WHERE metric_date >= ? AND metric_date <= ? AND platform IN ({marks})
                GROUP BY metric_date ORDER BY metric_date""",
            (start.isoformat(), end.isoformat(), *chosen),
        )
        return [{"date": row["metric_date"], "mentions": round(row["mentions"] or 0), "search_interest": round(row["search_interest"] or 0, 1)} for row in rows]

    def platform_breakdown(self, start: date, end: date, platforms: Iterable[str]) -> List[Dict[str, Any]]:
        chosen = list(platforms)
        if not chosen:
            return []
        marks = ", ".join("?" for _ in chosen)
        rows = self.fetchall(
            f"""SELECT platform, SUM(metric_value) AS mentions
                FROM pulse_daily_metrics
                WHERE metric_date >= ? AND metric_date <= ? AND platform IN ({marks}) AND metric_name='mentions'
                GROUP BY platform ORDER BY mentions DESC""",
            (start.isoformat(), end.isoformat(), *chosen),
        )
        return [{"platform": row["platform"], "mentions": round(row["mentions"] or 0)} for row in rows]

    def recent_mentions(self, start: date, end: date, platforms: Iterable[str], limit: int = 50) -> List[Dict[str, Any]]:
        chosen = list(platforms)
        if not chosen:
            return []
        marks = ", ".join("?" for _ in chosen)
        return self.fetchall(
            f"""SELECT platform, source_url, title, published_at, matched_term, engagement_count,
                       estimated_reach, sentiment, sentiment_confidence
                FROM pulse_mentions
                WHERE substr(published_at, 1, 10) >= ? AND substr(published_at, 1, 10) <= ?
                AND platform IN ({marks})
                ORDER BY published_at DESC LIMIT ?""",
            (start.isoformat(), end.isoformat(), *chosen, limit),
        )

    def freshness(self) -> List[Dict[str, Any]]:
        return self.fetchall(
            """SELECT platform, MAX(finished_at) AS last_attempt_at,
                      MAX(CASE WHEN status='success' THEN finished_at END) AS last_success_at,
                      MAX(latest_available_at) AS latest_available_at,
                      (SELECT status FROM pulse_sync_runs latest
                       WHERE latest.platform = pulse_sync_runs.platform
                       ORDER BY latest.finished_at DESC LIMIT 1) AS status
               FROM pulse_sync_runs GROUP BY platform ORDER BY platform"""
        )


def matched_term(text: str, terms: Iterable[str]) -> Optional[str]:
    lowered = (text or "").lower()
    return next((term for term in terms if term.lower() in lowered), None)


def collect_search_console(store: PulseStore, start: date, end: date, terms: List[str], geography: str) -> int:
    """Collect branded organic Google search performance for the owned website."""
    site_url = os.getenv("GSC_SITE_URL", "")
    raw_credentials = os.getenv("GSC_SERVICE_ACCOUNT_JSON", "")
    if not site_url or not raw_credentials:
        raise RuntimeError("Skipped: add GSC_SITE_URL and GSC_SERVICE_ACCOUNT_JSON.")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Google Search Console packages are not installed.") from exc
    try:
        credentials_info = json.loads(raw_credentials)
    except json.JSONDecodeError:
        credentials_info = json.loads(base64.b64decode(raw_credentials).decode("utf-8"))
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    unique_rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for term in terms:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["date", "query"],
            "dimensionFilterGroups": [{"filters": [{"dimension": "query", "operator": "contains", "expression": term}]}],
            "rowLimit": 25000,
        }
        for row in service.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows", []):
            keys = row.get("keys", [])
            if len(keys) == 2:
                unique_rows[(keys[0], keys[1].lower())] = row
    daily: Dict[str, Dict[str, float]] = defaultdict(lambda: {"clicks": 0, "impressions": 0})
    for (metric_day, _query), row in unique_rows.items():
        daily[metric_day]["clicks"] += float(row.get("clicks", 0))
        daily[metric_day]["impressions"] += float(row.get("impressions", 0))
    for metric_day, values in daily.items():
        day = date.fromisoformat(metric_day)
        store.upsert_metric(day, "google", "brand_search_clicks", values["clicks"], geography=geography)
        store.upsert_metric(day, "google", "brand_search_impressions", values["impressions"], geography=geography)
    store.commit()
    return len(unique_rows)


def collect_reddit(store: PulseStore, start: date, terms: List[str]) -> int:
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("Skipped: add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.")
    try:
        import praw
    except ImportError as exc:
        raise RuntimeError("PRAW is not installed.") from exc
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=os.getenv("REDDIT_USER_AGENT", "CoBasDaughterBrandPulse/1.0"),
    )
    count = 0
    seen = set()
    for term in terms:
        for submission in reddit.subreddit("all").search(f'"{term}"', sort="new", time_filter="week", limit=100):
            if submission.id in seen:
                continue
            seen.add(submission.id)
            published = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if published.date() < start:
                continue
            title = submission.title or ""
            label, confidence = sentiment_for(title)
            store.upsert_mention({
                "external_key": f"reddit:{submission.id}",
                "platform": "reddit",
                "external_id": submission.id,
                "source_url": f"https://reddit.com{submission.permalink}",
                "title": title,
                "published_at": published,
                "matched_term": matched_term(title, terms) or term,
                "engagement_count": int(submission.score or 0) + int(submission.num_comments or 0),
                "sentiment": label,
                "sentiment_confidence": confidence,
                "metadata": {"subreddit": str(submission.subreddit), "score": int(submission.score or 0), "comments": int(submission.num_comments or 0)},
            })
            count += 1
    store.commit()
    return count


def collect_instagram_owned(store: PulseStore, start: date, terms: List[str]) -> int:
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
    if not token or not account_id:
        raise RuntimeError("Skipped: add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID.")
    url = f"https://graph.facebook.com/v22.0/{account_id}/media"
    params = {"access_token": token, "fields": "id,caption,permalink,like_count,comments_count,timestamp,media_type", "limit": 100}
    count = 0
    while url:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        for media in payload.get("data", []):
            published = parse_iso_datetime(media.get("timestamp"))
            if as_date(published) < start:
                continue
            text = media.get("caption") or ""
            term = matched_term(text, terms)
            if not term:
                continue
            label, confidence = sentiment_for(text)
            store.upsert_mention({
                "external_key": f"instagram:{media['id']}",
                "platform": "instagram",
                "external_id": media["id"],
                "source_url": media.get("permalink") or "",
                "title": text,
                "published_at": published,
                "matched_term": term,
                "engagement_count": int(media.get("like_count") or 0) + int(media.get("comments_count") or 0),
                "sentiment": label,
                "sentiment_confidence": confidence,
                "metadata": {"media_type": media.get("media_type")},
            })
            count += 1
        url = (payload.get("paging") or {}).get("next")
        params = {}
    store.commit()
    return count


def collect_tiktok_provider(store: PulseStore, start: date, end: date, terms: List[str]) -> int:
    """Ingest from an approved commercial provider using a documented JSON contract.

    This avoids pretending that TikTok's research-only API can serve a commercial
    brand-monitoring product. The provider endpoint returns {'items': [...]}.
    """
    endpoint = os.getenv("TIKTOK_APPROVED_PROVIDER_URL", "")
    token = os.getenv("TIKTOK_APPROVED_PROVIDER_TOKEN", "")
    if not endpoint or not token:
        raise RuntimeError("Skipped: add an approved commercial TikTok provider URL and token.")
    response = requests.get(
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
        params={"query": " OR ".join(terms), "from": start.isoformat(), "to": end.isoformat()},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", payload.get("data", []))
    if not isinstance(items, list):
        raise RuntimeError("TikTok provider response must contain an items list.")
    count = 0
    for item in items:
        external_id = str(item.get("id") or item.get("video_id") or "")
        if not external_id:
            continue
        title = str(item.get("caption") or item.get("title") or "")
        term = matched_term(title, terms) or "CoBa's Daughter"
        label, confidence = sentiment_for(title)
        store.upsert_mention({
            "external_key": f"tiktok:{external_id}",
            "platform": "tiktok",
            "external_id": external_id,
            "source_url": item.get("url") or item.get("share_url") or "",
            "title": title,
            "published_at": item.get("published_at") or item.get("create_time"),
            "matched_term": term,
            "engagement_count": int(item.get("engagement") or item.get("like_count") or 0) + int(item.get("comment_count") or 0) + int(item.get("share_count") or 0),
            "estimated_reach": int(item.get("reach") or item.get("view_count") or 0),
            "sentiment": item.get("sentiment") or label,
            "sentiment_confidence": float(item.get("sentiment_confidence") or confidence),
            "metadata": {"provider": "approved", "raw_metrics": item.get("metrics", {})},
        })
        count += 1
    store.commit()
    return count


def import_keyword_metrics_csv(store: PulseStore, csv_text: str, geography: str = "global") -> int:
    """Import an approved Google Ads / Trends export, useful until an API is enabled.

    CSV columns: date, metric_name, metric_value. Optional: platform, brand_term.
    """
    count = 0
    for row in csv.DictReader(io.StringIO(csv_text)):
        try:
            store.upsert_metric(
                date.fromisoformat(row["date"]),
                row.get("platform") or "google",
                row["metric_name"],
                float(row["metric_value"]),
                row.get("brand_term") or "all",
                geography,
            )
            count += 1
        except (KeyError, ValueError) as exc:
            raise ValueError("Keyword metric CSV needs date, metric_name, and metric_value columns.") from exc
    store.commit()
    return count


def run_daily_sync(days: int = 7, database_url: Optional[str] = None) -> Dict[str, Any]:
    """Collect approved sources, write them atomically, and refresh daily aggregates."""
    store = PulseStore(database_url)
    end = date.today()
    start = end - timedelta(days=max(1, days) - 1)
    terms = parse_terms(os.getenv("BRAND_PULSE_TERMS", ""))
    geography = os.getenv("BRAND_PULSE_GEOGRAPHY", "global")
    results: Dict[str, Any] = {"start": start.isoformat(), "end": end.isoformat(), "sources": {}}
    collectors = {
        "google_search_console": lambda: collect_search_console(store, start, end, terms, geography),
        "reddit": lambda: collect_reddit(store, start, terms),
        "instagram": lambda: collect_instagram_owned(store, start, terms),
        "tiktok": lambda: collect_tiktok_provider(store, start, end, terms),
    }
    for platform, collector in collectors.items():
        started = utc_now()
        try:
            written = collector()
            store.record_sync(platform, started, "success", written)
            results["sources"][platform] = {"status": "success", "records_written": written}
        except Exception as exc:  # Keep one disconnected source from blocking every other source.
            store.connection.rollback()
            message = str(exc) if str(exc).startswith('Skipped:') else 'Collection failed; check provider access and configuration.'
            status = "skipped" if message.startswith("Skipped:") else "failed"
            store.record_sync(platform, started, status, 0, detail=message)
            results["sources"][platform] = {"status": status, "detail": message}
            logger.warning("Brand Pulse %s: %s", platform, message)
    store.refresh_mention_metrics(start, end, geography)
    store.close()
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Collect CoBa's Daughter Brand Pulse data")
    parser.add_argument("--days", type=int, default=7, help="Backfill this many days on every run")
    parser.add_argument("--database-url", default=None, help="Override BRAND_PULSE_DATABASE_URL")
    parser.add_argument("--keyword-csv", default="", help="Import an approved Google keyword CSV instead of collecting")
    args = parser.parse_args()
    if args.keyword_csv:
        store = PulseStore(args.database_url)
        with open(args.keyword_csv, encoding="utf-8") as source:
            total = import_keyword_metrics_csv(store, source.read(), os.getenv("BRAND_PULSE_GEOGRAPHY", "global"))
        store.close()
        print(json.dumps({"status": "success", "metrics_imported": total}))
        return
    result = run_daily_sync(args.days, args.database_url)
    print(json.dumps(result, indent=2))
    if any(source['status'] == 'failed' for source in result['sources'].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
