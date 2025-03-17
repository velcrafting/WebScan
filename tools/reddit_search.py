import praw
import pandas as pd
import json
import config
import prawcore
import datetime

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
            'score': comment.score,  # extra field (currently not used)
            'body': comment.body,
            'created': pd.to_datetime(comment.created_utc, unit='s'),
            'upvotes': comment.ups,  # using upvotes in formatted output
            'downvotes': comment.downs,  # extra field
            'comment_id': comment.id,
            'parent_id': comment.parent_id
        })
    return top_comments

def format_top_comments(comments):
    """
    Converts a list of comment dictionaries into a readable string format.
    Each comment is formatted as: "author (upvotes): comment body"
    """
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
            return {
                'name': 'N/A',
                'flair': 'N/A',       # extra field
                'karma': 'N/A',       # extra field
                'created': 'N/A'      # extra field
            }
        author_info = {
            'name': author.name if hasattr(author, 'name') else 'N/A',
            'flair': author.flair if hasattr(author, 'flair') else 'N/A',         # extra field
            'karma': (author.link_karma + author.comment_karma) if hasattr(author, 'link_karma') and hasattr(author, 'comment_karma') else 'N/A',  # extra field
            'created': pd.to_datetime(author.created_utc, unit='s') if hasattr(author, 'created_utc') else 'N/A'  # extra field
        }
    except (AttributeError, prawcore.exceptions.NotFound):
        author_info = {
            'name': 'N/A',
            'flair': 'N/A',       # extra field
            'karma': 'N/A',       # extra field
            'created': 'N/A'      # extra field
        }
    return author_info

def search_reddit(client, keyword, max_results=15, subreddit='all'):
    """
    Searches Reddit for a given keyword using both "new" and "top" sorts.
    If the same submission appears in both, the "type" field is updated to list both.
    """
    # Convert keyword to lowercase for case-insensitive search
    keyword = keyword.lower()
    results = {}
    
    for sort in ['new', 'top']:
        print(f"  Searching '{keyword}' sorted by {sort.upper()}...")
        for submission in client.subreddit(subreddit).search(keyword, sort=sort, limit=max_results):
            sub_id = submission.id
            author_info = get_author_info(submission.author)
            top_comments = fetch_top_comments(submission)
            formatted_comments = format_top_comments(top_comments)
            data = {
                'search term': keyword,
                'type': sort,  # initial sort type; may be updated below
                'title': submission.title,
                'upvotes': submission.ups,  # using upvotes instead of score
                '# of comments': submission.num_comments,
                'author': author_info['name'],
                'created': pd.to_datetime(submission.created_utc, unit='s'),
                'url': submission.url,
                'content': submission.selftext,
                'flair': submission.link_flair_text,
                'subreddit': submission.subreddit.display_name,
                'top comments': formatted_comments,
                'submission_id': sub_id  # internal field for deduplication
                # Extra fields (commented out for future extensibility):
                # 'score': submission.score,  
                # 'author_flair': author_info['flair'],
                # 'author_karma': author_info['karma'],
                # 'author_created': author_info['created'],
                # 'downvotes': submission.downs,
                # 'nsfw': submission.over_18,
                # 'media': submission.media['reddit_video']['fallback_url'] if submission.media and 'reddit_video' in submission.media else None,
            }
            if sub_id in results:
                # If this submission already exists, update the "type" field to include both values.
                existing_types = set([t.strip() for t in results[sub_id]['type'].split(',')])
                existing_types.add(sort)
                results[sub_id]['type'] = ", ".join(sorted(existing_types))
            else:
                results[sub_id] = data

    # Remove the internal submission_id before returning results.
    posts = []
    for sub_id, data in results.items():
        data.pop('submission_id', None)
        posts.append(data)
    return posts

def scrape_reddit(client, keywords, limit=15, subreddit='all'):
    all_posts = []
    for keyword in keywords:
        print(f"\nSearching Reddit for keyword: '{keyword}' in subreddit: '{subreddit}'")
        posts = search_reddit(client, keyword, max_results=limit, subreddit=subreddit)
        post_count = len(posts)
        print(f"Completed search for '{keyword}'. Posts found: {post_count}")
        all_posts.extend(posts)

    if not all_posts:
        print("No posts found for the provided keywords.")
        return pd.DataFrame()

    df = pd.DataFrame(all_posts)
    return df

def run_reddit_search():
    """
    Interactive Reddit search:
      - Prompts for keyword source and subreddit.
      - Provides progress feedback during the search.
      - Saves output as reddit_search_results_<date>.csv.
    """
    print("\n--- Reddit Search ---")
    
    # Choose keyword source
    use_file = input("Would you like to use keywords from keywords.json? (Y/N): ").strip().lower()
    if use_file == 'y':
        try:
            with open("data/keywords.json", 'r') as f:
                keywords = json.load(f)
            if not keywords:
                raise ValueError("keywords.json is empty")
            print(f"Loaded keywords: {', '.join(keywords)}")
        except Exception as e:
            print(f"Error loading keywords.json ({e}). Please enter keywords manually.")
            keywords_input = input("Enter comma-separated keywords to search on Reddit: ").strip()
            keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
    else:
        keywords_input = input("Enter comma-separated keywords to search on Reddit: ").strip()
        keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
    
    if not keywords:
        print("No keywords provided. Exiting Reddit search.")
        return

    # Prompt for subreddit (default is 'all')
    subreddit = input("Enter the subreddit to search (default 'all'): ").strip()
    if not subreddit:
        subreddit = 'all'
    
    # Prompt for maximum results per sort type
    limit_input = input("Enter the number of posts per sort (default 15): ").strip()
    try:
        max_results = int(limit_input) if limit_input else 15
    except ValueError:
        print("Invalid number entered. Using default of 15.")
        max_results = 15

    print("\nInitializing Reddit client...")
    reddit = init_reddit_client()
    
    print("Starting Reddit search. Please wait...\n")
    df = scrape_reddit(reddit, keywords, limit=max_results, subreddit=subreddit)
    
    if df.empty:
        print("No posts were found for the given keywords.")
    else:
        # Format output file with current date (e.g., reddit_search_results_feb18.csv)
        date_str = datetime.datetime.now().strftime("%b%d").lower()
        output_path = f"output/reddit_search_results_{date_str}.csv"
        df.to_csv(output_path, index=False)
        print(f"\nReddit search complete. Total posts found: {len(df)}")
        print(f"Results have been saved to: {output_path}")
