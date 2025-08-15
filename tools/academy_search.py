import os
import csv
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from random import uniform

# =======================
# FILE PATHS
# =======================
DATA_DIR = "data"
OUTPUT_DIR = "output"
INPUT_DIR = "input"

CSV_IMPORT_FILE = os.path.join(INPUT_DIR, "academy_articles_import.csv")
ARTICLES_FILE = os.path.join(DATA_DIR, "academy_articles.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "academy_scrape_log.txt")

# Ensure necessary directories exist
for directory in [DATA_DIR, OUTPUT_DIR, INPUT_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# =======================
# KEYWORDS TO SEARCH
# =======================
KEYWORDS = ["Device", "Hardware Wallet", "Cold Storage Wallet", "Ledger Live", "Bolos OS", "Partner", "Provider", "swap provider", "swap partner", "Crypto Wallet", "Ledger Wallet"]

# =======================
# SMART RATE LIMITING
# =======================
def fetch_page(url, retries=3):
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(retries):
        try:
            print(f"🌐 Fetching: {url}")
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            elif response.status_code == 429:
                wait_time = 2 ** attempt + uniform(1, 3)
                print(f"⚠️ Rate limited. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
    print(f"❌ Failed to retrieve page after {retries} attempts.")
    log_failure(url, "Failed to fetch page")
    return None

# =======================
# LOGGING FUNCTION
# =======================
def log_failure(url, reason):
    """ Log failures to an output file for future inspection. """
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} - {url} - {reason}\n")

# =======================
# OFFLINE SYNC: CSV → JSON
# =======================
def load_and_sync_articles():
    """ Load academy_articles.json and merge with CSV data if available. """
    print("🔍 Loading existing academy articles...")
    
    # Load JSON data
    existing_articles = []
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, "r") as f:
            existing_articles = json.load(f)

    existing_links = {article.get("link") for article in existing_articles}
    
    # Load CSV data if it exists
    if os.path.exists(CSV_IMPORT_FILE):
        print("📥 Merging data from academy_articles_import.csv...")
        with open(CSV_IMPORT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = row.get("Link", "").strip()
                if link and link not in existing_links:
                    new_article = {
                        "link": link,
                        "title": row.get("Article", "Unknown Title").strip(),
                        "category": row.get("Category", "Unknown Category").strip(),
                        "publish_date": row.get("Publish Date", "Unknown Date").strip(),
                        "update_date": row.get("Update Date", "Unknown Date").strip(),
                        "type": row.get("Type", "Unknown Type").strip(),
                        "translations": {},
                        "Keywords": {}
                    }
                    existing_articles.append(new_article)
                    existing_links.add(link)
    
    # Save back to JSON
    with open(ARTICLES_FILE, "w") as f:
        json.dump(existing_articles, f, indent=4)
    
    print(f"✅ Merged articles saved to {ARTICLES_FILE}")
    return existing_articles

# =======================
# SCRAPE AND UPDATE ARTICLE
# =======================
def scrape_article(article):
    """ Scrapes the page for keywords and updates the article details. """
    url = article["link"]
    soup = fetch_page(url)
    if not soup:
        print(f"❌ Failed to scrape article: {url}")
        log_failure(url, "Scrape failed (no soup object)")
        return None

    # Title extraction if not present
    if not article.get("title") or article["title"] == "Unknown Title":
        article["title"] = soup.find("h1").text.strip() if soup.find("h1") else "Unknown Title"
        if article["title"] == "Unknown Title":
            log_failure(url, "Title not found on page")

    # Description (first 3 paragraphs)
    description = ""
    article_div = soup.find(id="article")
    if article_div:
        paragraphs = article_div.find_all("p")
        description = " ".join(p.text.strip() for p in paragraphs[:3])
    
    article["description"] = description
    
    # Keyword counting
    text = soup.get_text().lower()
    article["Keywords"] = {keyword: text.count(keyword.lower()) for keyword in KEYWORDS}
    return article

# =======================
# SAVE RESULTS TO CSV (Including URL)
# =======================
def save_to_csv(articles):
    """Export the article data to a CSV file, including URL."""
    date_str = datetime.now().strftime("%m%d%y")
    filename = os.path.join(OUTPUT_DIR, f"ledger_academy_articles_{date_str}.csv")
    
    headers = ["URL", "Title", "Description", "Publish Date", "Last Edit", "Category", "Type"] + KEYWORDS
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for article in articles:
            row = {
                "URL": article.get("link", ""),
                "Title": article.get("title", ""),
                "Description": article.get("description", ""),
                "Publish Date": article.get("publish_date", ""),
                "Last Edit": article.get("update_date", ""),
                "Category": article.get("category", ""),
                "Type": article.get("type", "")
            }
            for keyword in KEYWORDS:
                row[keyword] = article["Keywords"].get(keyword, 0)
            writer.writerow(row)

    print(f"✅ Data saved to {filename}")

# =======================
# MAIN FUNCTION
# =======================
def run_academy_keyword_scan():
    print("🚀 Starting Academy Scraper & Keyword Scan...")
    
    # **1️⃣ Offline Sync**
    articles = load_and_sync_articles()
    
    # **2️⃣ Web Scrape**
    for idx, article in enumerate(articles):
        print(f"🔎 Scraping Article {idx + 1}/{len(articles)}")
        updated_article = scrape_article(article)
        if updated_article:
            articles[idx] = updated_article

    # **3️⃣ Save Results**
    save_to_csv(articles)
    with open(ARTICLES_FILE, "w") as f:
        json.dump(articles, f, indent=4)

    print("✅ Scan, Update, and Save complete.")