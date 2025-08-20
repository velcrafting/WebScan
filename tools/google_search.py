import time
import random
import requests
import csv
import os
from datetime import datetime
import config
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# =======================
# CONSTANTS
# =======================
GOOGLE_RESULTS_PER_QUERY = 10
GOOGLE_QUERY_DELAY_MIN = 2
GOOGLE_QUERY_DELAY_MAX = 4
METADATA_FETCH_DELAY_MIN = 3
METADATA_FETCH_DELAY_MAX = 5
DAILY_QUERY_LIMIT = 100
QUERY_COUNT = 0

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
HEADERS = {'User-Agent': USER_AGENT}

session = requests.Session()
session.headers.update(HEADERS)

# =======================
# HELPER FUNCTIONS
# =======================
def sleep_random(min_sec, max_sec):
    """Pause execution randomly within a range."""
    sleep_time = random.uniform(min_sec, max_sec)
    print(f"Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

def extract_domain(url):
    """Extracts the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "")

def get_output_filename(base_name="google_search_results", folder="output"):
    """
    Generates an output filename with the current date in the format 'MonDD'
    and appends a numeric suffix if a file already exists.
    """
    date_str = datetime.now().strftime("%b%d")  # e.g., Feb18
    base_filename = f"{base_name}_{date_str}.csv"
    output_path = os.path.join(folder, base_filename)
    if not os.path.exists(output_path):
        return output_path
    else:
        suffix = 1
        while os.path.exists(os.path.join(folder, f"{base_name}_{date_str}-{suffix}.csv")):
            suffix += 1
        return os.path.join(folder, f"{base_name}_{date_str}-{suffix}.csv")

# =======================
# METADATA EXTRACTION
# =======================
def fetch_metadata(url):
    """Scrape metadata from a given URL including title, description,
       publication date, last edit date, and author."""
    try:
        print(f"Fetching metadata for URL: {url}")
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Title and description
        title = soup.find('title').text.strip() if soup.find('title') else 'No Title'
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = (description_tag.get('content', '').strip() 
                       if description_tag and description_tag.get('content') 
                       else 'No Description')
        
        # Publication Date
        pub_date_tag = soup.find("meta", property="article:published_time")
        if not pub_date_tag:
            pub_date_tag = soup.find("meta", attrs={"name": "pubdate"})
        publication_date = (pub_date_tag.get("content", "").strip() 
                            if pub_date_tag and pub_date_tag.get("content") 
                            else "N/A")
        
        # Last Edit Date
        last_edit_tag = soup.find("meta", property="article:modified_time")
        if not last_edit_tag:
            last_edit_tag = soup.find("meta", attrs={"name": "lastmod"})
        last_edit_date = (last_edit_tag.get("content", "").strip() 
                          if last_edit_tag and last_edit_tag.get("content") 
                          else "N/A")
        
        # Author
        author_tag = soup.find("meta", attrs={"name": "author"})
        if not author_tag:
            author_tag = soup.find("meta", property="article:author")
        author = (author_tag.get("content", "").strip() 
                  if author_tag and author_tag.get("content") 
                  else "N/A")
        
        return {
            'title': title,
            'description': description,
            'publication_date': publication_date,
            'last_edit_date': last_edit_date,
            'author': author
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata for {url}: {e}")
        return {
            'title': 'Error',
            'description': 'Error',
            'publication_date': 'Error',
            'last_edit_date': 'Error',
            'author': 'Error'
        }

# =======================
# GOOGLE SEARCH FUNCTIONS
# =======================
def search_google(keyword, site=None):
    """Perform Google Custom Search API request."""
    global QUERY_COUNT
    if QUERY_COUNT >= DAILY_QUERY_LIMIT:
        print("Daily query limit reached.")
        return []

    query = f"site:{site} {keyword}" if site else keyword
    params = {
        "q": query,
        "key": config.API_KEY,
        "cx": config.CSE_ID,
        "num": GOOGLE_RESULTS_PER_QUERY,
    }

    try:
        print(f"Performing Google search with query: {query}")
        response = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
        response.raise_for_status()
        QUERY_COUNT += 1
        items = response.json().get("items", [])
        print(f"Received {len(items)} result(s).")
        return [{'url': item['link'], 'keyword': keyword} for item in items]
    except requests.exceptions.RequestException as e:
        print(f"Error during Google search for query '{query}': {e}")
        return []

def run_google_search(websites, keywords, pages_per_keyword):
    """Executes the Google Search process."""
    all_results = []
    print("Starting Google Search Process...")

    for site in websites:
        print(f"\nProcessing site: {site}")
        for kw in keywords:
            print(f"  Searching for keyword: '{kw}'")
            for page in range(1, pages_per_keyword + 1):
                print(f"    Page {page}/{pages_per_keyword}: Performing search query...")
                results = search_google(kw, site)
                if results:
                    print(f"      Found {len(results)} result(s).")
                else:
                    print("      No results found or API error.")
                for res in results:
                    print(f"        Fetching metadata for URL: {res['url']}")
                    metadata = fetch_metadata(res['url'])
                    print(f"          Metadata: Title: {metadata['title']}")
                    all_results.append({
                        'Website': site,
                        'Keyword': kw,
                        'URL': res['url'],
                        'Title': metadata.get('title', ''),
                        'Description': metadata.get('description', ''),
                        'Publication Date': metadata.get('publication_date', ''),
                        'Last Edit Date': metadata.get('last_edit_date', ''),
                        'Author': metadata.get('author', '')
                    })
                sleep_random(GOOGLE_QUERY_DELAY_MIN, GOOGLE_QUERY_DELAY_MAX)

    output_file = get_output_filename()
    fieldnames = ['Website', 'Keyword', 'URL', 'Title', 'Description', 
                  'Publication Date', 'Last Edit Date', 'Author']
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nGoogle Search complete. Results saved to {output_file}")
    except Exception as e:
        print(f"Error writing results to {output_file}: {e}")
