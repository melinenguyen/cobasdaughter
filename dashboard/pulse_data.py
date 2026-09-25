"""Private, read-only provider collection. No legacy messaging integrations."""
import base64
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import psycopg
import requests
from cryptography.fernet import Fernet


def database():
    return psycopg.connect(os.environ['BRAND_PULSE_DATABASE_URL'], connect_timeout=10)


def cipher():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(
        os.environ['BRAND_PULSE_TOKEN_KEY'].encode()).digest()))


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS pulse_live_runs (
        provider TEXT PRIMARY KEY, status TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
        detail TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS pulse_live_search (
        site TEXT NOT NULL, day DATE NOT NULL, clicks DOUBLE PRECISION NOT NULL,
        impressions DOUBLE PRECISION NOT NULL, position DOUBLE PRECISION NOT NULL,
        PRIMARY KEY(site, day))''')
    db.execute('''CREATE TABLE IF NOT EXISTS pulse_live_videos (
        account TEXT NOT NULL, video TEXT NOT NULL, observed DATE NOT NULL,
        published DATE NOT NULL, likes BIGINT, comments BIGINT, shares BIGINT, views BIGINT,
        PRIMARY KEY(account, video, observed))''')
    db.commit()


def status(db, provider, state, detail):
    db.execute('''INSERT INTO pulse_live_runs VALUES (%s,%s,NOW(),%s)
        ON CONFLICT(provider) DO UPDATE SET status=EXCLUDED.status,
        updated_at=EXCLUDED.updated_at, detail=EXCLUDED.detail''', (provider, state, detail))
    db.commit()


def refresh(db, provider, account, encrypted):
    tokens = json.loads(cipher().decrypt(encrypted.encode()))
    if provider == 'tiktok':
        url = 'https://open.tiktokapis.com/v2/oauth/token/'
        credentials = {'client_key': os.environ['TIKTOK_CLIENT_KEY'],
                       'client_secret': os.environ['TIKTOK_CLIENT_SECRET']}
    else:
        url = 'https://oauth2.googleapis.com/token'
        credentials = {'client_id': os.environ['GOOGLE_CLIENT_ID'],
                       'client_secret': os.environ['GOOGLE_CLIENT_SECRET']}
    response = requests.post(url, data=dict(credentials, grant_type='refresh_token',
        refresh_token=tokens['refresh_token']), timeout=20)
    response.raise_for_status()
    refreshed = response.json()
    if not refreshed.get('access_token'):
        raise ValueError('Authorization needs attention')
    tokens.update(refreshed)
    tokens['obtained_at'] = time.time()
    # Persist rotated refresh tokens before making any collection request.
    db.execute('''UPDATE pulse_oauth_connections SET encrypted_tokens=%s, updated_at=%s
        WHERE provider=%s AND account_id=%s''',
        (cipher().encrypt(json.dumps(tokens).encode()).decode(), time.time(), provider, account))
    db.commit()
    return tokens


def google(db, account, tokens):
    end = datetime.now(timezone.utc).date() - timedelta(days=4)
    start = end - timedelta(days=399)
    response = requests.post('https://www.googleapis.com/webmasters/v3/sites/' +
        quote(account, safe='') + '/searchAnalytics/query',
        headers={'Authorization': 'Bearer ' + tokens['access_token']},
        json={'startDate': str(start), 'endDate': str(end), 'dimensions': ['date'],
              'type': 'web', 'dataState': 'final', 'rowLimit': 25000,
              'dimensionFilterGroups': [{'filters': [{'dimension': 'query',
                  'operator': 'includingRegex',
                  'expression': "(?i)co\\s*ba['’]?s?\\s*daughter"}]}]}, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or 'error' in payload:
        raise ValueError('Invalid search result')
    rows = payload.get('rows', [])
    # Replace only this successful reporting window; omissions stay unknown.
    with db.transaction():
        db.execute('DELETE FROM pulse_live_search WHERE site=%s AND day BETWEEN %s AND %s',
                   (account, start, end))
        for row in rows:
            db.execute('INSERT INTO pulse_live_search VALUES (%s,%s,%s,%s,%s)',
                       (account, row['keys'][0], row['clicks'], row['impressions'], row['position']))
    return 'success', f'{len(rows)} reported days loaded; branded web search only. Missing days are not filled with zero.'


def tiktok(db, account, tokens):
    observed = datetime.now(timezone.utc).date()
    cursor = None
    videos = {}
    complete = False
    for _ in range(25):
        body = {'max_count': 20}
        if cursor is not None:
            body['cursor'] = cursor
        response = requests.post('https://open.tiktokapis.com/v2/video/list/',
            params={'fields': 'id,create_time,like_count,comment_count,share_count,view_count'},
            headers={'Authorization': 'Bearer ' + tokens['access_token']}, json=body, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if payload.get('error', {}).get('code') != 'ok':
            raise ValueError('Video request rejected')
        data = payload['data']
        for video in data.get('videos', []):
            videos[video['id']] = video
        if not data.get('has_more'):
            complete = True
            break
        next_cursor = data.get('cursor')
        if next_cursor is None or next_cursor == cursor:
            raise ValueError('Pagination did not progress')
        cursor = next_cursor
    with db.transaction():
        # Replace the account's same-day snapshot, never accumulate duplicates.
        db.execute('DELETE FROM pulse_live_videos WHERE account=%s AND observed=%s', (account, observed))
        for video in videos.values():
            db.execute('INSERT INTO pulse_live_videos VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (account, video['id'], observed,
                 datetime.fromtimestamp(video['create_time'], timezone.utc).date(),
                 video.get('like_count'), video.get('comment_count'),
                 video.get('share_count'), video.get('view_count')))
    return ('success' if complete else 'partial'), (
        f'{len(videos)} authorized-account videos collected. Lifetime engagement snapshot.' +
        ('' if complete else ' The 500-video safety limit was reached; inventory is partial.'))


def collect():
    """Bounded background task. Session advisory lock prevents concurrent refreshes."""
    try:
        with database() as db:
            schema(db)
            locked = db.execute('SELECT pg_try_advisory_lock(71420953)').fetchone()[0]
            db.commit()
            if not locked:
                return
            try:
                if not db.execute("SELECT to_regclass('pulse_oauth_connections')").fetchone()[0]:
                    return
                connections = db.execute('''SELECT provider, account_id, encrypted_tokens
                    FROM pulse_oauth_connections WHERE provider IN ('tiktok','google_search_console')''').fetchall()
                db.commit()
                for provider, account, encrypted in connections:
                    status(db, provider, 'running', 'Reading authorized data. Reload in about a minute.')
                    try:
                        tokens = refresh(db, provider, account, encrypted)
                        state, detail = (tiktok if provider == 'tiktok' else google)(db, account, tokens)
                        status(db, provider, state, detail)
                    except Exception:
                        db.rollback()
                        status(db, provider, 'error', 'Collection failed; previous data preserved. Check permissions or reconnect in Private setup. Provider errors are hidden to protect credentials.')
            finally:
                db.execute('SELECT pg_advisory_unlock(71420953)')
                db.commit()
    except Exception:
        # Never log provider request URLs, tokens, or database credentials.
        return


def read_dashboard(start, end):
    """Only aggregate values leave the server, never tokens or account identifiers."""
    with database() as db:
        schema(db)
        runs = [{'source': r[0], 'status': r[1], 'updated': r[2].isoformat(), 'detail': r[3]}
                for r in db.execute('SELECT * FROM pulse_live_runs ORDER BY provider').fetchall()]
        search = [{'day': str(r[0]), 'clicks': r[1], 'impressions': r[2]} for r in db.execute(
            '''SELECT day,SUM(clicks),SUM(impressions) FROM pulse_live_search
               WHERE day BETWEEN %s AND %s GROUP BY day ORDER BY day''', (start, end)).fetchall()]
        videos = [{'day': str(r[0]), 'posts': r[1], 'likes': r[2], 'comments': r[3], 'views': r[4]}
            for r in db.execute('''SELECT observed,COUNT(*),SUM(likes),SUM(comments),SUM(views)
                FROM pulse_live_videos WHERE observed BETWEEN %s AND %s
                GROUP BY observed ORDER BY observed''', (start, end)).fetchall()]
        instagram = []
        if db.execute("SELECT to_regclass('pulse_owned_instagram_snapshots')").fetchone()[0]:
            instagram = [{'day': r[0], 'posts': r[1], 'likes': r[2], 'comments': r[3]}
                for r in db.execute('''SELECT day,COUNT(*),SUM(likes),SUM(comments) FROM
                    (SELECT DISTINCT ON (account_id,media_id,substring(observed_at,1,10))
                    substring(observed_at,1,10) AS day,likes,comments
                    FROM pulse_owned_instagram_snapshots
                    WHERE substring(observed_at,1,10) BETWEEN %s AND %s
                    ORDER BY account_id,media_id,substring(observed_at,1,10),observed_at DESC) latest
                    GROUP BY day ORDER BY day''', (str(start), str(end))).fetchall()]
        return {'search': search, 'tiktok': videos, 'instagram': instagram, 'runs': runs}
