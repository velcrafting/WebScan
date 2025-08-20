import os
import json
import csv
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

# =======================
# CONFIGURATION
# =======================
SCRAPE_DELAY = 5.0

# =======================
# FILE PATHS
# =======================
DATA_DIR = "data"
OUTPUT_DIR = "output"
INPUT_DIR = "input"  # Folder for raw CSV input

ARTICLES_FILE = os.path.join(DATA_DIR, "academy_articles.json")
CSV_IMPORT_FILE = os.path.join(INPUT_DIR, "academy_articles_import.csv")

# Ensure necessary directories exist
for directory in [DATA_DIR, OUTPUT_DIR, INPUT_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# =======================
# LANGUAGE REGION CODES
# =======================
LANGUAGES = {
    "English (en)": "en",
    "Arabic (ar)": "ar",
    "Chinese Simplified (zh-hans)": "zh-hans",
    "French (fr)": "fr",
    "German (de)": "de",
    "Russian (ru)": "ru",
    "Spanish (es)": "es",
    "Portuguese (pt-br)": "pt-br",
    "Turkish (tr)": "tr",
    "Japanese (ja)": "ja",
    "Korean (ko)": "ko",
}

BASE_URL = "https://www.ledger.com/academy"

# =======================
# HELPER FUNCTIONS
# =======================
def load_json(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(data, filepath):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

def clean_url(url):
    url = url.strip()
    if url.startswith("https://www.ledger.comhttps://"):
        url = url.replace("https://www.ledger.comhttps://", "https://www.ledger.com/")
    return url

def get_soup(url):
    url = clean_url(url)
    print(f"DEBUG: Fetching URL: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        response = requests.get(url, headers=headers)
        time.sleep(SCRAPE_DELAY)
    except Exception as e:
        print(f"❌ Error during requests.get: {e}")
        return None

    if response.status_code != 200:
        print(f"❌ Received status code {response.status_code} for URL: {url}")
        return None
    return BeautifulSoup(response.text, "html.parser")

def scrape_article(url):
    """Scrape article details from the given URL."""
    url = clean_url(url)
    if not url.startswith("http"):
        url = f"https://www.ledger.com{url}"
        url = clean_url(url)
    soup = get_soup(url)
    if not soup:
        print(f"❌ Failed to retrieve article: {url}")
        return None

    title = soup.find("h1").text.strip() if soup.find("h1") else "Unknown Title"
    article_div = soup.find(id="article")
    description = ""
    if article_div:
        paragraphs = article_div.find_all("p")
        description = " ".join(p.text.strip() for p in paragraphs[:3])
    dates = soup.find_all("time")
    publish_date = dates[0].text.strip() if len(dates) > 0 else "Unknown"
    last_edit_date = dates[1].text.strip() if len(dates) > 1 else publish_date

    return {
        "title": title,
        "description": description,
        "publish_date": publish_date,
        "last_edit_date": last_edit_date,
        "link": url,
    }

def discover_articles():
    """Discover article URLs from the Ledger Academy main page."""
    soup = get_soup(BASE_URL)
    if not soup:
        print("❌ Failed to retrieve Academy page.")
        return []
    articles_set = set()
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if "/academy/topics/" in href:
            if href.startswith("http"):
                full_url = href
            else:
                full_url = f"https://www.ledger.com{href}"
            full_url = clean_url(full_url)
            articles_set.add(full_url)
    # Preserve order
    return list(dict.fromkeys(articles_set))

def check_translation_exists(url):
    """
    Check if a translated page exists by first sending a HEAD request and,
    if successful, performing a GET request to verify expected content.
    In this example, we check for the presence of an <h1> tag.
    """
    try:
        head_resp = requests.head(url, timeout=10)
        if head_resp.status_code != 200:
            return False

        # Lightweight GET to confirm valid page content.
        get_resp = requests.get(url, timeout=10)
        if "<h1" in get_resp.text:
            return True
        return False

    except Exception as e:
        print(f"❌ Error checking translation for {url}: {e}")
        return False

def check_translations(base_url):
    """
    Loop through all language codes and check if the translated page exists.
    Returns a dictionary with "Y" if the translation exists, else "N".
    """
    results = {}
    for lang, code in LANGUAGES.items():
        # Construct the translated URL by inserting the language code.
        translated_url = base_url.replace("/academy/", f"/{code}/academy/")
        results[lang] = "Y" if check_translation_exists(translated_url) else "N"
    return results

def save_to_csv(data):
    """Export the article data (including translation status) to a CSV file."""
    date_str = datetime.now().strftime("%m%d%y")
    filename = os.path.join(OUTPUT_DIR, f"ledger_academy_articles_{date_str}.csv")
    headers = [
        "Title", "Description", "Publish Date", "Last Edit",
        "Category", "Type", "English (en)"
    ] + list(list(LANGUAGES.keys())[1:])
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for entry in data:
            row = {
                "Title": entry.get("title", ""),
                "Description": entry.get("description", ""),
                "Publish Date": entry.get("publish_date", ""),
                "Last Edit": entry.get("last_edit_date", ""),
                "Category": entry.get("category", ""),
                "Type": entry.get("type", ""),
                "English (en)": "Y" if entry.get("link") else "N",
            }
            translations = entry.get("translations", {})
            for lang in list(LANGUAGES.keys())[1:]:
                row[lang] = translations.get(lang, "N")
            writer.writerow(row)
    print(f"✅ Data saved to {filename}")

def import_article_sheet(csv_filepath):
    """
    Import articles from a CSV file.
    The CSV should have the columns: Article (title), Link (url), Category,
    Publish Date, Update Date, and Type.
    """
    articles = []
    try:
        with open(csv_filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                article = {
                    "title": row.get("Article", "").strip(),
                    "link": clean_url(row.get("Link", "").strip()),
                    "category": row.get("Category", "").strip(),
                    "publish_date": row.get("Publish Date", "").strip(),
                    "update_date": row.get("Update Date", "").strip(),
                    "type": row.get("Type", "").strip(),
                    "translations": {}
                }
                articles.append(article)
    except Exception as e:
        print(f"❌ Error importing CSV data: {e}")
    return articles

def update_article(article):
    """
    Update a given article dict by scraping its page (to get description, etc.)
    and then checking for translation availability.
    CSV-imported metadata (e.g., category, update_date, type) will be preserved.
    """
    scraped = scrape_article(article.get("link"))
    if scraped:
        # Merge scraped data (CSV data will override if already present)
        article["title"] = scraped.get("title", article.get("title", ""))
        article["description"] = scraped.get("description", article.get("description", ""))
        article["publish_date"] = scraped.get("publish_date", article.get("publish_date", ""))
        # Use scraped last_edit_date or CSV's update_date (if present)
        article["last_edit_date"] = scraped.get("last_edit_date", article.get("update_date", article.get("publish_date", "")))
        article["link"] = scraped.get("link", article.get("link", ""))
    article["translations"] = check_translations(article.get("link", ""))
    return article

# =======================
# MAIN FUNCTION
# =======================
def run_academy_scraper():
    print("\nLedger Academy Scraper Options:")
    print("1. Scrape existing articles from academy_articles.json")
    print("2. Crawl for new articles and add them")
    print("3. Scrape new and existing articles (combine)")
    print("4. Scrape targeted articles (enter URLs manually)")
    print("5. Import articles from CSV file")
    
    choice = input("Enter choice (1-5): ").strip()
    articles = load_json(ARTICLES_FILE)
    # Determine if articles is a list of URLs (strings) or dictionaries
    articles_list = []
    if articles:
        if isinstance(articles[0], dict):
            articles_list = articles
        else:
            articles_list = [{"link": url} for url in articles]
    
    if choice == "1":
        if not articles_list:
            print("❌ No existing articles found in academy_articles.json.")
            return
        confirm = input("Scrape all articles in academy_articles.json? (Y/N): ").strip().lower()
        if confirm != "y":
            return

    elif choice == "2":
        discovered = discover_articles()
        new_articles = []
        for url in discovered:
            if not any(a.get("link") == url for a in articles_list):
                new_articles.append({"link": url})
        num_input = input("How many new articles? (Enter a number or 'all'): ").strip().lower()
        if num_input != "all":
            try:
                limit = int(num_input)
                new_articles = new_articles[:limit]
            except ValueError:
                print("Invalid number. Using all new articles.")
        articles_list.extend(new_articles)

    elif choice == "3":
        discovered = discover_articles()
        new_articles = []
        for url in discovered:
            if not any(a.get("link") == url for a in articles_list):
                new_articles.append({"link": url})
        num_input = input("How many additional new articles? (Enter a number or 'all'): ").strip().lower()
        if num_input != "all":
            try:
                limit = int(num_input)
                new_articles = new_articles[:limit]
            except ValueError:
                print("Invalid number. Using all new articles.")
        articles_list.extend(new_articles)

    elif choice == "4":
        urls = input("Enter article URLs (comma-separated): ").strip().split(",")
        new_urls = [clean_url(url) for url in urls if url.strip()]
        for url in new_urls:
            if not any(a.get("link") == url for a in articles_list):
                articles_list.append({"link": url})

    elif choice == "5":
        # Automatically use the CSV file from the input folder
        if not os.path.exists(CSV_IMPORT_FILE):
            print(f"❌ CSV file not found at {CSV_IMPORT_FILE}. Please ensure it exists in the input folder.")
            return
        imported_articles = import_article_sheet(CSV_IMPORT_FILE)
        if not imported_articles:
            print("❌ No articles imported from CSV.")
            return
        
        total_imported = len(imported_articles)
        new_records = 0
        for art in imported_articles:
            exists = False
            for existing in articles_list:
                if existing.get("link") == art.get("link"):
                    exists = True
                    break
            if not exists:
                articles_list.append(art)
                new_records += 1
        save_json(articles_list, ARTICLES_FILE)
        print(f"✅ Import complete: {new_records} new record(s) added out of {total_imported} total record(s) provided.")
        return  # Exit without proceeding to full scrape

    else:
        print("❌ Invalid choice.")
        return

    # If not using import-only, continue with scraping process:
    # Remove duplicates (based on the link)
    unique_articles = []
    seen = set()
    for art in articles_list:
        link = art.get("link")
        if link and link not in seen:
            seen.add(link)
            unique_articles.append(art)
    articles_list = unique_articles
    save_json(articles_list, ARTICLES_FILE)

    # Update each article (scrape details and check translations)
    results = []
    for art in articles_list:
        updated = update_article(art)
        results.append(updated)

    save_to_csv(results)
    print("✅ Scraping complete.")

if __name__ == "__main__":
    run_academy_scraper()
