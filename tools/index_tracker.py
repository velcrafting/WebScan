from datetime import datetime, timedelta
import pandas as pd
import config
from . import reddit_search, google_search, storage

TRACK_CSV = 'output/geo_index_tracking.csv'
TRACK_JSON = 'output/geo_index_tracking.json'


def start_tracking(subreddits, count):
    reddit = reddit_search.get_reddit()
    existing = storage.load_csv(TRACK_CSV)
    existing_ids = {row['post_id'] for row in existing}
    rows = []
    for sub in subreddits:
        for submission in reddit.subreddit(sub).new(limit=count):
            if submission.id in existing_ids:
                continue
            rows.append({
                'post_id': submission.id,
                'url': submission.url,
                'subreddit': sub,
                'created_utc': datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                'first_seen_google_utc': '',
                'delta_minutes': ''
            })
    for row in rows:
        storage.append_csv(TRACK_CSV, row, ['post_id', 'url', 'subreddit', 'created_utc', 'first_seen_google_utc', 'delta_minutes'])
    data = existing + rows
    storage.write_json(TRACK_JSON, data)
    return rows


def check_indexing():
    rows = storage.load_csv(TRACK_CSV)
    updated = False
    for row in rows:
        if row.get('first_seen_google_utc'):
            continue
        if google_search.search_url(row['url']):
            now = datetime.utcnow()
            row['first_seen_google_utc'] = now.isoformat()
            created = datetime.fromisoformat(row['created_utc'])
            delta = int((now - created).total_seconds() / 60)
            row['delta_minutes'] = str(delta)
            updated = True
    if updated:
        storage.write_csv(TRACK_CSV, rows, ['post_id', 'url', 'subreddit', 'created_utc', 'first_seen_google_utc', 'delta_minutes'])
        storage.write_json(TRACK_JSON, rows)
    df = pd.DataFrame(rows)
    df = df[df['delta_minutes'] != '']
    if df.empty:
        return {}
    df['created_utc'] = pd.to_datetime(df['created_utc'])
    df['delta_minutes'] = pd.to_numeric(df['delta_minutes'])
    recent = df[df['created_utc'] >= datetime.utcnow() - timedelta(days=60)]
    if recent.empty:
        return {}
    stats = {
        'min': float(recent['delta_minutes'].min()),
        'median': float(recent['delta_minutes'].median()),
        'p95': float(recent['delta_minutes'].quantile(0.95)),
        'n': len(recent)
    }
    return stats