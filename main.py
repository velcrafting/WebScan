import os
import sys
import argparse
from datetime import datetime
import time

# Ensure tools directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))

from tools import cli, scheduler, storage, reddit_search, sentiment, themes, geo, seo
# ---------------------------------------------------------------------------
# Engagement utilities
# ---------------------------------------------------------------------------
def run_eng_brand_activity(users_file: str, lookback: int):
    reddit = reddit_search.init_reddit_client()
    users = storage.load_json(users_file, [])
    end_ts = int(time.time())
    start_ts = end_ts - lookback * 24 * 3600
    rows = []
    for user in users:
        try:
            redditor = reddit.redditor(user)
            for c in redditor.comments.new(limit=None):
                if c.created_utc < start_ts:
                    break
                rows.append({
                    'user': user,
                    'type': 'comment',
                    'subreddit': c.subreddit.display_name,
                    'score': c.score,
                    'created_utc': datetime.utcfromtimestamp(c.created_utc).isoformat(),
                })
            for s in redditor.submissions.new(limit=None):
                if s.created_utc < start_ts:
                    break
                rows.append({
                    'user': user,
                    'type': 'post',
                    'subreddit': s.subreddit.display_name,
                    'score': s.score,
                    'created_utc': datetime.utcfromtimestamp(s.created_utc).isoformat(),
                    'url': s.url,
                })
        except Exception as e:
            rows.append({'user': user, 'error': str(e)})
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'brand_activity_{ts}.json')
    storage.write_json(out_path, rows)
    print(f"Saved activity for {len(users)} user(s) to {out_path}")

def run_eng_fud_scan(subs_file: str, lookback: int, limit: int, rules_file: str):
    reddit = reddit_search.init_reddit_client()
    subreddits = storage.load_json(subs_file, [])
    rules = themes.load_rules(rules_file) if os.path.exists(rules_file) else {}
    start_ts = int(time.time()) - lookback * 24 * 3600
    results = []
    for sub in subreddits:
        df = reddit_search.scrape_reddit(
            reddit, keywords=[], limit=limit, subreddit=sub, start_ts=start_ts,
            highlight_terms=None, fetch_comments=False
        )
        for row in df.to_dict('records'):
            text = f"{row.get('title', '')} {row.get('content', '')}"
            tone = sentiment.tone_from_text(text)
            theme = themes.classify(text, rules) if rules else None
            row.update({'tone': tone, 'theme': theme})
            results.append(row)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'fud_scan_{ts}.json')
    storage.write_json(out_path, results)
    print(f"Saved {len(results)} post(s) to {out_path}")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
def run_scheduler():
    scheduler.schedule_jobs()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="WebScan CLI")
    sub = parser.add_subparsers(dest='command')

    sp_serp = sub.add_parser('geo:serp-reddit', help='Collect Reddit results from Google SERP')
    sp_serp.add_argument('--queries', required=True, help='Path to queries JSON file')
    sp_serp.add_argument('--top', type=int, default=5, help='Top N reddit results to keep')

    sp_probe = sub.add_parser('geo:llm-probe', help='Probe LLM providers for references')
    sp_probe.add_argument('--queries', required=True, help='Path to queries JSON file')

    sub.add_parser('geo:index-check', help='Check Google indexing for tracked Reddit posts')

    sp_meta = sub.add_parser('seo:serp-metadata', help='Fetch metadata from top search results')
    sp_meta.add_argument('--queries', required=True, help='Path to queries JSON file')
    sp_meta.add_argument('--top', type=int, default=5, help='Top N results to analyze')

    sp_brand = sub.add_parser('eng:brand-activity', help='Collect recent activity for brand accounts')
    sp_brand.add_argument('--users', required=True, help='Path to reddit usernames JSON file')
    sp_brand.add_argument('--lookback', type=int, default=60, help='Lookback window in days')

    sp_fud = sub.add_parser('eng:fud-scan', help='Scan subreddits for negative sentiment')
    sp_fud.add_argument('--subreddits', required=True, help='Path to subreddits JSON file')
    sp_fud.add_argument('--lookback', type=int, default=14, help='Lookback window in days')
    sp_fud.add_argument('--limit', type=int, default=400, help='Posts to fetch per subreddit')
    sp_fud.add_argument('--rules', default=os.path.join('data', 'theme_rules.json'), help='Path to theme rules JSON')

    sub.add_parser('scheduler', help='Run scheduled jobs')

    return parser.parse_args()


def main():
    args = parse_args()
    if not args.command:
        cli.main_menu()
        return

    if args.command == 'geo:serp-reddit':
        out_path, count = geo.serp_reddit(args.queries, args.top)
        print(f"Saved {count} result(s) to {out_path}")
    elif args.command == 'geo:llm-probe':
        out_path, count = geo.llm_probe_queries(args.queries)
        print(f"Saved {count} probe result(s) to {out_path}")
    elif args.command == 'geo:index-check':
        stats = geo.index_check()
        if stats:
            print("Indexing stats:", stats)
        else:
            print("No recent indexed posts found.")
    elif args.command == 'seo:serp-metadata':
        out_path, count = seo.serp_metadata(args.queries, args.top)
        print(f"Saved metadata for {count} result(s) to {out_path}")
    elif args.command == 'eng:brand-activity':
        run_eng_brand_activity(args.users, args.lookback)
    elif args.command == 'eng:fud-scan':
        run_eng_fud_scan(args.subreddits, args.lookback, args.limit, args.rules)
    elif args.command == 'scheduler':
        run_scheduler()


if __name__ == '__main__':
    main()