import praw
import pandas as pd
import json
import config
import prawcore
import datetime
import time


def init_reddit_client():
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT
    )
    return reddit


def fetch_top_comments(submission, limit=3):
    submission.comment_sort = 'top'
    submission.comments.replace_more(limit=0)
    top_comments = []
    for comment in submission.comments[:limit]:
        top_comments.append({
            'author': comment.author.name if comment.author else 'N/A',
            'score': comment.score,
            'body': comment.body,
            'created': pd.to_datetime(comment.created_utc, unit='s'),
            'upvotes': comment.ups,
            'downvotes': comment.downs,
            'comment_id': comment.id,
            'parent_id': comment.parent_id
        })
    return top_comments


def format_top_comments(comments):
    if not comments:
        return ""
    formatted = []
    for comment in comments:
        line = f"{comment['author']} ({comment['upvotes']} upvotes): {comment['body']}"
        formatted.append(line)
    return "\n".join(formatted)


def get_author_info(author):
    try:
        if author is None:
            return {'name': 'N/A', 'flair': 'N/A', 'karma': 'N/A', 'created': 'N/A'}
        author_info = {
            'name': author.name if hasattr(author, 'name') else 'N/A',
            'flair': author.flair if hasattr(author, 'flair') else 'N/A',
            'karma': (author.link_karma + author.comment_karma) if hasattr(author, 'link_karma') and hasattr(author, 'comment_karma') else 'N/A',
            'created': pd.to_datetime(author.created_utc, unit='s') if hasattr(author, 'created_utc') else 'N/A'
        }
    except (AttributeError, prawcore.exceptions.NotFound):
        author_info = {'name': 'N/A', 'flair': 'N/A', 'karma': 'N/A', 'created': 'N/A'}
    return author_info


def highlight_keywords(text, keywords):
    if not keywords or not text:
        return []
    text_lower = text.lower()
    return list({kw for kw in keywords if kw.lower() in text_lower})


def summarize_scan(df, subreddit, start_str, end_str, highlight_terms, summary_path=None):
    total_posts = len(df)
    total_upvotes = df['upvotes'].sum()
    total_comments = df['# of comments'].sum()
    date_range = pd.to_datetime(df['created'])
    days = max((date_range.max() - date_range.min()).days, 1)
    posts_per_day = total_posts / days
    upvotes_per_post = total_upvotes / total_posts if total_posts else 0
    comments_per_post = total_comments / total_posts if total_posts else 0

    flagged_df = df[df['highlighted_keywords'].apply(lambda x: bool(x))]
    flagged_posts = len(flagged_df)
    flagged_upvotes = flagged_df['upvotes'].sum()
    flagged_comments = flagged_df['# of comments'].sum()
    flagged_posts_per_day = flagged_posts / days if days else 0
    flagged_upvotes_per_post = flagged_upvotes / flagged_posts if flagged_posts else 0
    flagged_comments_per_post = flagged_comments / flagged_posts if flagged_posts else 0

    summary = f"""
Scan Summary for subreddit: {subreddit}
Date Range: {start_str} to {end_str}

Total Posts: {total_posts}
Total Comments: {total_comments}
Total Upvotes: {total_upvotes}
Average Posts Per Day: {posts_per_day:.2f}
Average Upvotes Per Post: {upvotes_per_post:.2f}
Average Comments Per Post: {comments_per_post:.2f}

Flagged Posts Matching Highlighted Keywords: {flagged_posts}
Total Comments (Flagged): {flagged_comments}
Total Upvotes (Flagged): {flagged_upvotes}
Average Flagged Posts Per Day: {flagged_posts_per_day:.2f}
Average Upvotes Per Flagged Post: {flagged_upvotes_per_post:.2f}
Average Comments Per Flagged Post: {flagged_comments_per_post:.2f}
"""

    print(summary)

    if summary_path:
        with open(summary_path, 'w') as f:
            f.write(summary)


def search_all_subreddit_posts(client, subreddit='all', limit=None, start_ts=None, end_ts=None, highlight_terms=None, fetch_comments=True):
    results = {}
    print(f"  Scanning subreddit '{subreddit}' with {'no limit' if limit is None else f'limit={limit}'}...")
    count = 0
    for submission in client.subreddit(subreddit).new(limit=None):
        if end_ts and submission.created_utc > end_ts:
            continue
        if start_ts and submission.created_utc < start_ts:
            break  # Stop once posts get older than the start date

        sub_id = submission.id
        if sub_id in results:
            continue

        author_info = get_author_info(submission.author)

        top_comments = []
        formatted_comments = ""
        if fetch_comments:
            time.sleep(1)  # prevent 429 rate limit
            try:
                top_comments = fetch_top_comments(submission)
                formatted_comments = format_top_comments(top_comments)
            except Exception as e:
                print(f"  Skipped comments for post {sub_id} due to error: {e}")

        tags = set()
        for field in [submission.title, submission.selftext, formatted_comments]:
            tags.update(highlight_keywords(field, highlight_terms))

        results[sub_id] = {
            'search term': 'ALL',
            'type': 'new',
            'title': submission.title,
            'upvotes': submission.ups,
            '# of comments': submission.num_comments,
            'author': author_info['name'],
            'created': pd.to_datetime(submission.created_utc, unit='s'),
            'url': submission.url,
            'content': submission.selftext,
            'flair': submission.link_flair_text,
            'subreddit': submission.subreddit.display_name,
            'top comments': formatted_comments,
            'highlighted_keywords': list(tags)
        }

        count += 1
        if limit and count >= limit:
            break

    return list(results.values())


def scrape_reddit(client, keywords, limit=None, subreddit='all', start_ts=None, end_ts=None, highlight_terms=None, fetch_comments=True):
    if not keywords:
        print(f"\nScanning ALL posts in subreddit: '{subreddit}'")
        posts = search_all_subreddit_posts(client, subreddit=subreddit, limit=limit, start_ts=start_ts, end_ts=end_ts, highlight_terms=highlight_terms, fetch_comments=fetch_comments)
        return pd.DataFrame(posts)

    all_posts = []
    for keyword in keywords:
        print(f"\nSearching Reddit for keyword: '{keyword}' in subreddit: '{subreddit}'")
        posts = search_all_subreddit_posts(client, subreddit=subreddit, limit=limit, start_ts=start_ts, end_ts=end_ts, highlight_terms=highlight_terms, fetch_comments=fetch_comments)
        all_posts.extend(posts)

    if not all_posts:
        print("No posts found for the provided keywords.")
        return pd.DataFrame()

    return pd.DataFrame(all_posts)


def get_keywords_from_user():
    use_file = input("Would you like to use keywords from keywords.json? (Y/N): ").strip().lower()
    keywords = []
    if use_file == 'y':
        try:
            with open("data/keywords.json", 'r') as f:
                keywords = json.load(f)
            print(f"Loaded keywords: {', '.join(keywords)}")
        except Exception as e:
            print(f"Error loading keywords.json ({e}). Continuing with manual entry.")

    manual_input = input("Enter additional comma-separated keywords (or leave blank to search ALL posts): ").strip()
    if manual_input:
        manual_keywords = [kw.strip() for kw in manual_input.split(",") if kw.strip()]
        keywords = list(set(keywords + manual_keywords))

    return keywords


def summarize_inputs(keywords, subreddit, max_results, start_str, end_str, highlight_terms):
    print("\nSummary of your Reddit search:")
    print(f"- Keywords: {', '.join(keywords) if keywords else '[ALL POSTS]'}")
    print(f"- Subreddit: {subreddit}")
    print(f"- Date Range: {start_str} - {end_str}")
    print(f"- Post Limit: {max_results if max_results else '[ALL AVAILABLE]'}")
    print(f"- Highlight Terms: {', '.join(highlight_terms) if highlight_terms else '[None]'}")
    confirm = input("Proceed with search? (Y/N): ").strip().lower()
    return confirm == 'y'


def run_reddit_search():
    print("\n--- Reddit Search ---")

    keywords = get_keywords_from_user()
    subreddit = input("Enter the subreddit to search (default 'all'): ").strip() or 'all'

    limit_input = input("Enter the number of posts to scan (leave blank to fetch all available): ").strip()
    try:
        max_results = int(limit_input) if limit_input else None
    except ValueError:
        print("Invalid number entered. Using full scan mode.")
        max_results = None

    start_input = input("Enter start date (MM/YY): ").strip()
    end_input = input("Enter end date (MM/YY) or press Enter for today: ").strip()

    def parse_date(mm_yy):
        return int(time.mktime(datetime.datetime.strptime(f"01/{mm_yy}", "%d/%m/%y").timetuple()))

    try:
        start_ts = parse_date(start_input)
        start_str = datetime.datetime.fromtimestamp(start_ts).strftime("%b %Y")
    except Exception:
        print("Invalid start date. Using beginning of time.")
        start_ts = None
        start_str = 'Beginning'

    try:
        end_ts = parse_date(end_input) if end_input else int(time.time())
        end_str = datetime.datetime.fromtimestamp(end_ts).strftime("%b %Y")
    except Exception:
        print("Invalid end date. Using current time.")
        end_ts = int(time.time())
        end_str = 'Now'

    highlight_input = input("Enter comma-separated keywords to highlight (or press Enter to reuse search keywords): ").strip()
    if highlight_input:
        highlight_terms = [kw.strip() for kw in highlight_input.split(",") if kw.strip()]
    else:
        highlight_terms = keywords

    if not summarize_inputs(keywords, subreddit, max_results, start_str, end_str, highlight_terms):
        print("Search cancelled.")
        return

    print("\nInitializing Reddit client...")
    reddit = init_reddit_client()

    print("Starting Reddit search. Please wait...\n")
    df = scrape_reddit(reddit, keywords, limit=max_results, subreddit=subreddit, start_ts=start_ts, end_ts=end_ts, highlight_terms=highlight_terms)

    if df.empty:
        print("No posts were found for the given keywords.")
    else:
        date_str = datetime.datetime.now().strftime("%b%d").lower()
        output_path = f"output/reddit_search_results_{date_str}.csv"
        summary_path = f"output/reddit_search_summary_{date_str}.txt"
        df.to_csv(output_path, index=False)
        summarize_scan(df, subreddit, start_str, end_str, highlight_terms, summary_path)
        print(f"\nReddit search complete. Total posts found: {len(df)}")
        print(f"Results saved to: {output_path}")
        print(f"Summary saved to: {summary_path}")
