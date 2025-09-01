import os
import re
from . import google_search, youtube_search, reddit_search, academy_search, storage, geo, helpcenter_search

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

KEYWORDS_FILE = os.path.join(DATA_DIR, 'keywords.json')
WEBSITES_FILE = os.path.join(DATA_DIR, 'websites.json')
YT_CHANNELS_FILE = os.path.join(DATA_DIR, 'yt_channels.json')
YT_VIDEOS_FILE = os.path.join(DATA_DIR, 'yt_videos.json')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path):
    return storage.load_json(path, [])

def save_json(data, path):
    storage.write_json(path, data)

# ---------------------------------------------------------------------------
# Google Search
# ---------------------------------------------------------------------------
def prompt_google_search():
    """Handles Google Search interaction with enhanced keyword and website selection."""
    existing_keywords = load_json(KEYWORDS_FILE)
    existing_websites = load_json(WEBSITES_FILE)

    print("\n--- Keyword Selection ---")
    print("1. Use existing keywords from keywords.json")
    print("2. Enter new keywords")
    keyword_choice = input("Select keyword source (1 or 2): ").strip()

    if keyword_choice == "1":
        keywords = existing_keywords.copy()
    elif keyword_choice == "2":
        new_keywords_input = input("Enter new keywords separated by comma: ").strip()
        new_keywords = [kw.strip() for kw in new_keywords_input.split(",") if kw.strip()]
        include_existing = input("Do you want to also search using keywords from keywords.json? (Y/N): ").strip().lower()
        keywords = list(set(existing_keywords + new_keywords)) if include_existing == 'y' else new_keywords
        add_to_file = input("Do you want to add these new keywords to keywords.json for future use? (Y/N): ").strip().lower()
        if add_to_file == 'y':
            updated_keywords = list(set(existing_keywords + new_keywords))
            save_json(updated_keywords, KEYWORDS_FILE)
    else:
        print("Invalid selection. Defaulting to using keywords from keywords.json.")
        keywords = existing_keywords.copy()

    print("\n--- Website Selection ---")
    print("1. Use existing websites from websites.json")
    print("2. Enter new website URLs")
    website_choice = input("Select website source (1 or 2): ").strip()

    if website_choice == "1":
        websites = existing_websites.copy()
    elif website_choice == "2":
        new_websites_input = input("Enter new website URLs separated by comma: ").strip()
        new_websites = [site.strip() for site in new_websites_input.split(",") if site.strip()]
        include_existing_sites = input("Do you want to also search using websites from websites.json? (Y/N): ").strip().lower()
        websites = list(set(existing_websites + new_websites)) if include_existing_sites == 'y' else new_websites
        add_to_file_websites = input("Do you want to add these new websites to websites.json for future use? (Y/N): ").strip().lower()
        if add_to_file_websites == 'y':
            updated_websites = list(set(existing_websites + new_websites))
            save_json(updated_websites, WEBSITES_FILE)
    else:
        print("Invalid selection. Defaulting to using websites from websites.json.")
        websites = existing_websites.copy()

    while True:
        pages_input = input("Enter number of pages per keyword (1-5): ").strip()
        try:
            pages_per_keyword = int(pages_input)
            if 1 <= pages_per_keyword <= 5:
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Invalid number. Try again.")

    confirm = input("Do you want to start the Google search? (Y/N): ").strip().lower()
    if confirm == 'y':
        print(f"\nStarting Google search with {len(keywords)} keyword(s), {len(websites)} website(s), {pages_per_keyword} page(s) per keyword...")
        google_search.run_google_search(websites, keywords, pages_per_keyword)

# ---------------------------------------------------------------------------
# YouTube Search
# ---------------------------------------------------------------------------
def extract_video_id(url_or_id):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id

def prompt_youtube_video_search():
    print("\n-- YouTube Video Search Options --")
    print("Provide a link to the video(s) you would like to search separated by a comma,")
    print("or press 1 to search comments for the previously searched YouTube videos.")

    video_list = load_json(YT_VIDEOS_FILE)
    user_input = input("\nEnter video URLs or IDs (comma-separated), or press 1: ").strip()

    if user_input == "1":
        if not video_list:
            print("No previously searched videos found.")
            return
    else:
        new_videos = [extract_video_id(vid.strip()) for vid in user_input.split(",") if vid.strip()]
        video_list.extend(new_videos)
        save_choice = input("Would you like to add these videos to yt_videos.json? (Y/N): ").strip().lower()
        if save_choice == 'y':
            save_json(video_list, YT_VIDEOS_FILE)

    search_all = input("Would you like to search all yt_videos.json as well? (Y/N): ").strip().lower()
    if search_all == 'y':
        video_list = load_json(YT_VIDEOS_FILE)

    mode_choice = input(
        "\nSelect comment search mode:\n" "1 - Use keywords from keywords.json to filter comments\n" "2 - Scrape all comments (raw mode)\n" "Enter 1 or 2: "
    ).strip()
    raw_mode = True if mode_choice == "2" else False

    confirm = input("Do you want to start the YouTube video comment search? (Y/N): ").strip().lower()
    if confirm == 'y':
        keywords = load_json(KEYWORDS_FILE)
        for vid in video_list:
            youtube_search.run_youtube_search(vid, keywords, raw_mode)

def prompt_youtube_channel_search():
    print("\n-- YouTube Channel Search Options --")
    print("Provide a link to the channel(s) you would like to search separated by a comma,")
    print("or press 1 to search comments for the previously searched YouTube channels.")

    channel_list = load_json(YT_CHANNELS_FILE)
    user_input = input("\nEnter channel URLs or IDs (comma-separated), or press 1: ").strip()

    if user_input == "1":
        if not channel_list:
            print("No previously searched channels found.")
            return
    else:
        new_channels = [ch.strip() for ch in user_input.split(",") if ch.strip()]
        channel_list.extend(new_channels)
        save_choice = input("Would you like to add these channels to yt_channels.json? (Y/N): ").strip().lower()
        if save_choice == 'y':
            save_json(channel_list, YT_CHANNELS_FILE)

    search_all = input("Would you like to search all yt_channels.json as well? (Y/N): ").strip().lower()
    if search_all == 'y':
        channel_list = load_json(YT_CHANNELS_FILE)

    mode_choice = input(
        "\nSelect comment search mode:\n" "1 - Use keywords from keywords.json to filter comments\n" "2 - Scrape all comments (raw mode)\n" "Enter 1 or 2: "
    ).strip()
    raw_mode = True if mode_choice == "2" else False

    confirm = input("Do you want to start the YouTube channel-wide comment search? (Y/N): ").strip().lower()
    if confirm == 'y':
        keywords = load_json(KEYWORDS_FILE)
        for ch in channel_list:
            youtube_search.run_channel_wide_search(ch, keywords, raw_mode)

def prompt_youtube_search():
    print("\n-- YouTube Search Options --")
    print("1. Search comments for video(s)")
    print("2. Search comments for entire channel(s)")
    choice = input("Choose an option (1-2): ").strip()

    if choice == "1":
        prompt_youtube_video_search()
    elif choice == "2":
        prompt_youtube_channel_search()
    else:
        print("Invalid choice. Please enter 1 or 2.")

# ---------------------------------------------------------------------------
# Ledger Academy Search
# ---------------------------------------------------------------------------
def prompt_ledger_academy_search():
    print("\n-- Ledger Academy Scraper Options --")
    print("1. Offline Sync (CSV → JSON)")
    print("2. Full Scrape (Web)")
    print("3. Export to CSV")
    print("4. Full Process (Sync, Scrape, and Export)")

    choice = input("Choose an option (1-4): ").strip()

    if choice == "1":
        print("🔄 Running Offline Sync (CSV → JSON)...")
        academy_search.load_and_sync_articles()
    elif choice == "2":
        print("🌐 Running Full Web Scrape...")
        academy_search.run_academy_keyword_scan()
    elif choice == "3":
        print("💾 Exporting Data to CSV...")
        articles = academy_search.load_and_sync_articles()
        academy_search.save_to_csv(articles)
    elif choice == "4":
        print("🗂 Running Full Process (Sync, Scrape, Export)...")
        academy_search.run_academy_keyword_scan()
    else:
        print("Invalid choice. Please enter 1, 2, 3, or 4.")

# ---------------------------------------------------------------------------
# GEO Report
# ---------------------------------------------------------------------------
def prompt_geo_report():
    print("\n-- GEO Report --")
    queries_path = input("Path to queries JSON file: ").strip()
    top_input = input("Top N Reddit results to keep (default 5): ").strip()
    try:
        top_n = int(top_input) if top_input else 5
    except ValueError:
        top_n = 5

    out_serp, count_serp = geo.serp_reddit(queries_path, top_n)
    print(f"Saved {count_serp} SERP result(s) to {out_serp}")

    out_probe, count_probe = geo.llm_probe_queries(queries_path)
    print(f"Saved {count_probe} probe result(s) to {out_probe}")

    stats = geo.index_check()
    if stats:
        print("Indexing stats:", stats)
    else:
        print("No recent indexed posts found.")


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------
def main_menu():
    while True:
        print("\n--- Search Options ---")
        print("1. Google Search")
        print("2. YouTube Comment Search")
        print("3. Reddit Search")
        print("4. Ledger Academy Scraper")
        print("5. Help Center Scraper")
        print("6. GEO Report")
        print("7. Exit")
        choice = input("Choose an option (1-7): ").strip()

        if choice == "1":
            prompt_google_search()
        elif choice == "2":
            prompt_youtube_search()
        elif choice == "3":
            reddit_search.run_reddit_search()
        elif choice == "4":
            prompt_ledger_academy_search()
        elif choice == "5":
            # Help Center
            print("\n-- Help Center Scraper --")
            print("1. Offline Sync (CSV → JSON)")
            print("2. Full Scrape (Web)")
            print("3. Export to CSV")
            print("4. Full Process (Sync, Scrape, Export)")
            sub = input("Choose an option (1-4): ").strip()
            if sub == "1":
                helpcenter_search.load_and_sync_articles()
            elif sub == "2":
                helpcenter_search.run_helpcenter_scrape()
            elif sub == "3":
                articles = helpcenter_search.load_and_sync_articles()
                helpcenter_search.save_to_csv(articles)
            elif sub == "4":
                helpcenter_search.run_helpcenter_scrape()
            else:
                print("Invalid choice. Please enter 1-4.")
        elif choice == "6":
            prompt_geo_report()
        elif choice == "7":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please enter 1-6.")
