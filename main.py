import json
import re
import os
import sys

# Import tools from the "tools" directory
sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))
import google_search
import youtube_search
import reddit_search
import academy_search  # Enhanced Ledger Academy Scraper

# =======================
# FILE PATHS
# =======================
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
TOOLS_DIR = 'tools'

KEYWORDS_FILE = os.path.join(DATA_DIR, 'keywords.json')
WEBSITES_FILE = os.path.join(DATA_DIR, 'websites.json')
YT_CHANNELS_FILE = os.path.join(DATA_DIR, 'yt_channels.json')
YT_VIDEOS_FILE = os.path.join(DATA_DIR, 'yt_videos.json')

# Ensure necessary directories exist
for directory in [DATA_DIR, OUTPUT_DIR, TOOLS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# =======================
# JSON HANDLERS
# =======================
def load_json(filepath):
    """Load JSON data from a file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_json(data, filepath):
    """Save JSON data to a file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

# =======================
# GOOGLE SEARCH
# =======================
def prompt_google_search():
    """Handles Google Search interaction with enhanced keyword and website selection."""
    existing_keywords = load_json(KEYWORDS_FILE)
    existing_websites = load_json(WEBSITES_FILE)
    
    # --- KEYWORD SELECTION ---
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
        if include_existing == 'y':
            keywords = list(set(existing_keywords + new_keywords))
        else:
            keywords = new_keywords

        add_to_file = input("Do you want to add these new keywords to keywords.json for future use? (Y/N): ").strip().lower()
        if add_to_file == 'y':
            updated_keywords = list(set(existing_keywords + new_keywords))
            save_json(updated_keywords, KEYWORDS_FILE)
    else:
        print("Invalid selection. Defaulting to using keywords from keywords.json.")
        keywords = existing_keywords.copy()

    # --- WEBSITE SELECTION ---
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
        if include_existing_sites == 'y':
            websites = list(set(existing_websites + new_websites))
        else:
            websites = new_websites

        add_to_file_websites = input("Do you want to add these new websites to websites.json for future use? (Y/N): ").strip().lower()
        if add_to_file_websites == 'y':
            updated_websites = list(set(existing_websites + new_websites))
            save_json(updated_websites, WEBSITES_FILE)
    else:
        print("Invalid selection. Defaulting to using websites from websites.json.")
        websites = existing_websites.copy()

    print(f"\nStarting Google search with {len(keywords)} keywords and {len(websites)} websites...")
    google_search.run_google_search(websites, keywords)

# =======================
# YOUTUBE SEARCH
# =======================
def prompt_youtube_search():
    """Handles YouTube Search options for both videos and channels."""
    print("\n-- YouTube Search Options --")
    print("1. Search comments for video(s)")
    print("2. Search comments for entire channel(s)")
    choice = input("Choose an option (1-2): ").strip()

    if choice == "1":
        youtube_search.prompt_youtube_video_search()
    elif choice == "2":
        youtube_search.prompt_youtube_channel_search()
    else:
        print("Invalid choice. Please enter 1 or 2.")

# =======================
# LEDGER ACADEMY SEARCH
# =======================
def prompt_ledger_academy_search():
    """Handles Ledger Academy Scraper"""
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

# =======================
# MAIN MENU
# =======================
def main():
    """Main script loop for selecting search options."""
    while True:
        print("\n--- Search Options ---")
        print("1. Google Search")
        print("2. YouTube Comment Search")
        print("3. Reddit Search")
        print("4. Ledger Academy Scraper")
        print("5. Exit")
        choice = input("Choose an option (1-5): ").strip()

        if choice == "1":
            prompt_google_search()
        elif choice == "2":
            prompt_youtube_search()
        elif choice == "3":
            reddit_search.run_reddit_search()
        elif choice == "4":
            prompt_ledger_academy_search()
        elif choice == "5":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()