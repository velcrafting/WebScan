import os
from collections import Counter
from datetime import datetime, timedelta
import pandas as pd
from . import google_search, llm_probe, index_tracker, storage, reddit_search


def serp_reddit(queries_file: str, top: int):
    """Collect top Reddit results from Google SERP for given queries."""
    queries = storage.load_json(queries_file, [])
    all_results = []
    for q in queries:
        results = google_search.search_google(q, site="reddit.com")
        reddit_hits = results[:top]
        for hit in reddit_hits:
            url = hit.get("url", "")
            parts = url.split("/")
            subreddit = parts[4] if len(parts) > 4 else ""
            hit.update({"query": q, "subreddit": subreddit})
            all_results.append(hit)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'serp_reddit_{ts}.json')
    storage.write_json(out_path, all_results)
    return out_path, len(all_results)


def llm_probe_queries(queries_file: str):
    """Probe LLM providers for references to the supplied queries."""
    queries = storage.load_json(queries_file, [])
    all_results = []
    for q in queries:
        all_results.extend(llm_probe.probe(q))
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'llm_probe_{ts}.json')
    storage.write_json(out_path, all_results)
    return out_path, len(all_results)


def index_check():
    """Check Google indexing for tracked Reddit posts."""
    return index_tracker.check_indexing()


def start_index_tracking(subreddits, count):
    """Start tracking newest Reddit posts for Google indexing."""
    return index_tracker.start_tracking(subreddits, count)


def ledger_activity(username: str, days: int = 60):
    """Calculate post and comment frequency for a user."""
    client = reddit_search.init_reddit_client()
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    user = client.redditor(username)

    posts = []
    for sub in user.submissions.new(limit=None):
        created = datetime.utcfromtimestamp(sub.created_utc)
        if created < start:
            break
        if created <= end:
            posts.append(created.date())

    comments = []
    for com in user.comments.new(limit=None):
        created = datetime.utcfromtimestamp(com.created_utc)
        if created < start:
            break
        if created <= end:
            comments.append(created.date())

    post_counts = Counter(posts)
    comment_counts = Counter(comments)
    total_posts = len(posts)
    total_comments = len(comments)
    avg_posts = total_posts / days
    avg_comments = total_comments / days
    top_post_day = post_counts.most_common(1)[0][0] if post_counts else None
    top_comment_day = comment_counts.most_common(1)[0][0] if comment_counts else None
    return {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "avg_posts_per_day": avg_posts,
        "avg_comments_per_day": avg_comments,
        "highest_posts_day": str(top_post_day) if top_post_day else "",
        "highest_comments_day": str(top_comment_day) if top_comment_day else "",
    }


def subreddit_activity(subreddit: str, days: int = 60):
    """Calculate post and comment volume for a subreddit."""
    client = reddit_search.init_reddit_client()
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    posts = []
    for sub in client.subreddit(subreddit).new(limit=None):
        created = datetime.utcfromtimestamp(sub.created_utc)
        if created < start:
            break
        if created <= end:
            posts.append({
                "date": created.date(),
                "upvotes": sub.ups,
                "comments": sub.num_comments,
            })

    df = pd.DataFrame(posts)
    if df.empty:
        return {}

    daily = df.groupby("date").agg({"upvotes": "sum", "comments": "sum", "date": "size"}).rename(columns={"date": "posts"})
    avg_upvotes = float(df["upvotes"].mean())
    avg_comments = float(df["comments"].mean())
    top_day = daily["posts"].idxmax()
    return {
        "total_posts": int(daily["posts"].sum()),
        "avg_upvotes": avg_upvotes,
        "avg_comments": avg_comments,
        "highest_volume_day": str(top_day),
        "daily": daily.reset_index().to_dict(orient="records"),
    }


def generate_report(data, path=None):
    """Write a simple JSON report of collected GEO metrics."""
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = path or os.path.join('output', f'geo_report_{ts}.json')
    storage.write_json(out_path, data)
    return out_path