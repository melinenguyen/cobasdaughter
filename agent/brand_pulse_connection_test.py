"""Private, bounded Instagram-to-Postgres smoke test; prints no credentials/content."""
import os
import sys
from datetime import datetime, timezone

import psycopg
import requests


def main():
    stage = "configuration"
    try:
        database = os.environ["BRAND_PULSE_DATABASE_URL"]
        token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
        account = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]
        if not database.startswith(("postgresql://", "postgres://")) or not token or not account.isdigit():
            raise ValueError("Missing or invalid configuration")
        stage = "Instagram read access"
        response = requests.get(
            f"https://graph.facebook.com/v26.0/{account}/media",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": "id,permalink,timestamp,like_count,comments_count", "limit": 5},
            timeout=30,
        )
        response.raise_for_status()
        posts = response.json()["data"]
        if not isinstance(posts, list) or not posts:
            raise ValueError("No posts returned")
        stage = "database write and read-back"
        observed = datetime.now(timezone.utc).isoformat()
        with psycopg.connect(database, connect_timeout=20) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""CREATE TABLE IF NOT EXISTS pulse_owned_instagram_snapshots (
                    account_id TEXT NOT NULL, media_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL, published_at TEXT,
                    source_url TEXT, likes INTEGER, comments INTEGER,
                    PRIMARY KEY(account_id, media_id, observed_at)
                )""")
                for post in posts:
                    cursor.execute("""INSERT INTO pulse_owned_instagram_snapshots
                        (account_id, media_id, observed_at, published_at, source_url, likes, comments)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (account, post["id"], observed, post.get("timestamp"),
                         post.get("permalink"), post.get("like_count"), post.get("comments_count")))
                cursor.execute("SELECT COUNT(*) FROM pulse_owned_instagram_snapshots WHERE account_id = %s AND observed_at = %s", (account, observed))
                if cursor.fetchone()[0] != len(posts):
                    raise ValueError("Read-back mismatch")
        print(f"PASS: {len(posts)} owned Instagram post snapshots saved and verified in PostgreSQL.")
        print("No emails or Slack messages sent. No daily schedule enabled. Reach and public mentions not tested.")
        return 0
    except Exception:
        # Provider/DB exceptions can contain credentials or private connection details.
        print(f"FAIL at {stage}. No exception details printed to protect credentials.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
