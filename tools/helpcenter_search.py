import os
import csv
import json
import time
import re
from datetime import datetime
from random import uniform

import requests
from bs4 import BeautifulSoup

# =======================
# FILE PATHS
# =======================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_DIR = os.path.join(BASE_DIR, "input")

CSV_IMPORT_FILE = os.path.join(INPUT_DIR, "helpcenter_articles_import.csv")
ARTICLES_FILE = os.path.join(DATA_DIR, "helpcenter_articles.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "helpcenter_scrape_log.txt")

for d in (DATA_DIR, OUTPUT_DIR, INPUT_DIR):
    os.makedirs(d, exist_ok=True)


# =======================
# Helpers
# =======================
def log_failure(url, reason):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()}\t{url}\t{reason}\n")


def fetch_page(url, retries=3):
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
    }
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            elif resp.status_code == 429:
                wait = 2 ** attempt + uniform(0.5, 2.5)
                time.sleep(wait)
            else:
                # Some sites send 200 after redirect to locale. Try once more without path tweaks.
                log_failure(url, f"HTTP {resp.status_code}")
                break
        except Exception as e:
            if attempt == retries - 1:
                log_failure(url, f"Exception: {e}")
            wait = 1.5 * (attempt + 1)
            time.sleep(wait)
    return None


# =======================
# Zendesk (Help Center) API helpers
# =======================
def _is_ledger_support(url: str) -> bool:
    return "support.ledger.com" in url


def _extract_article_id(url: str) -> str:
    m = re.search(r"/article/(?:[^/]*?)(\d+)", url)
    return m.group(1) if m else ""


def _zd_get_json(url: str, retries: int = 3):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(2 ** attempt + uniform(0.5, 1.5))
            else:
                log_failure(url, f"API HTTP {r.status_code}")
                return None
        except Exception as e:
            if attempt == retries - 1:
                log_failure(url, f"API exception: {e}")
            time.sleep(1.0 * (attempt + 1))
    return None


def _zd_article_by_id(host: str, article_id: str):
    api = f"https://{host}/api/v2/help_center/articles/{article_id}.json"
    return _zd_get_json(api)


def _zd_search_article(host: str, query: str):
    # Search by title words for best match
    api = f"https://{host}/api/v2/help_center/articles/search.json?query={requests.utils.quote(query)}"
    return _zd_get_json(api)


def _zd_section_name(host: str, section_id: int) -> str:
    api = f"https://{host}/api/v2/help_center/sections/{section_id}.json"
    data = _zd_get_json(api)
    if data and data.get("section"):
        return data["section"].get("name", "")
    return ""


def load_keywords():
    path = os.path.join(DATA_DIR, "keywords.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# =======================
# CSV → JSON merge
# =======================
def load_and_sync_articles():
    """
    Load helpcenter_articles.json and merge with CSV import if present.
    Expected CSV headers: Title, URL
    """
    print("🔍 Loading help center articles (CSV → JSON sync)...")
    existing = []
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    by_url = {a.get("url"): a for a in existing}

    added = 0
    if os.path.exists(CSV_IMPORT_FILE):
        with open(CSV_IMPORT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Accept multiple possible column names; fall back to any value that looks like a URL
                url = (
                    row.get("URL")
                    or row.get("Url")
                    or row.get("UrlName")
                    or row.get("Link")
                    or row.get("link")
                    or row.get("url")
                    or ""
                ).strip()
                if not url:
                    # Find first value containing http(s)
                    for v in row.values():
                        if isinstance(v, str) and v.startswith("http"):
                            url = v.strip()
                            break
                title = (row.get("Title") or row.get("title") or "").strip()
                if not url:
                    continue
                if url not in by_url:
                    by_url[url] = {
                        "url": url,
                        "title": title or "",
                        "publish_date": "",
                        "topic": "",
                        "summary": "",
                        "updated": "",
                        "keywords": {},
                    }
                    added += 1
                else:
                    if title and not by_url[url].get("title"):
                        by_url[url]["title"] = title

    merged = list(by_url.values())
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"✅ Sync complete. {len(merged)} total article(s), {added} added from CSV.")
    return merged


# =======================
# Extraction helpers (robust for Zendesk/Help Center)
# =======================
def _parse_json_ld_dates(soup):
    date_published = ""
    date_modified = ""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        # Could be an object or a list
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") in {"Article", "NewsArticle", "TechArticle"}:
                date_published = it.get("datePublished", it.get("dateCreated", date_published))
                date_modified = it.get("dateModified", it.get("dateUpdated", date_modified))
    return date_published, date_modified


def _extract_topic(soup):
    # Breadcrumbs often expose category/section on Zendesk
    # Try several selectors
    selectors = [
        "nav[aria-label='breadcrumbs'] a",
        "ol.breadcrumbs a",
        "ul.breadcrumbs a",
        "nav.breadcrumbs a",
    ]
    crumbs = []
    for sel in selectors:
        nodes = soup.select(sel)
        if nodes:
            crumbs = [n.get_text(strip=True) for n in nodes]
            break
    # Usually last is current page; take the second to last as topic/section
    if len(crumbs) >= 2:
        return crumbs[-2]

    # Fallback: meta articleSection
    meta = soup.find("meta", attrs={"name": "article:section"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    meta = soup.find("meta", attrs={"property": "article:section"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""


def _extract_summary(soup, max_paras=3):
    # Common Zendesk containers for article body
    containers = [
        ".article-body",
        "article.article .article-content",
        "article .article__body",
        "article",
    ]
    for sel in containers:
        node = soup.select_one(sel)
        if not node:
            continue
        paras = [p.get_text(" ", strip=True) for p in node.find_all("p") if p.get_text(strip=True)]
        if paras:
            return " ".join(paras[:max_paras])
    # Fallback: meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"].strip()
    meta_og_desc = soup.find("meta", attrs={"property": "og:description"})
    if meta_og_desc and meta_og_desc.get("content"):
        return meta_og_desc["content"].strip()

    # Fallback: first paragraphs anywhere
    paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    return " ".join(paras[:max_paras])


def _extract_dates(soup):
    # JSON-LD first
    pub, mod = _parse_json_ld_dates(soup)
    # Meta tags
    metas = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"itemprop": "datePublished"}),
        ("meta", {"name": "date"}),
        ("meta", {"name": "publish_date"}),
    ]
    for tag, attrs in metas:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content") and not pub:
            pub = el["content"].strip()

    metas_mod = [
        ("meta", {"property": "article:modified_time"}),
        ("meta", {"property": "og:updated_time"}),
        ("meta", {"itemprop": "dateModified"}),
    ]
    for tag, attrs in metas_mod:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content") and not mod:
            mod = el["content"].strip()

    # time tags
    if not pub:
        t = soup.find("time", attrs={"datetime": True})
        if t:
            pub = t.get("datetime", "").strip()

    # Normalize dates if possible
    def normalize(dt):
        if not dt:
            return ""
        dt = dt.strip()
        # Try parsing ISO or RFC-like
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(dt, fmt).strftime("%Y-%m-%d")
            except Exception:
                continue
        # Last resort: regex extract date
        m = re.search(r"(\d{4}-\d{2}-\d{2})", dt)
        return m.group(1) if m else dt

    return normalize(pub), normalize(mod)


def _count_keywords(text, keywords):
    t = text.lower()
    return {kw: t.count(kw.lower()) for kw in keywords}


# =======================
# Scrape single article
# =======================
def scrape_article(article):
    url = article.get("url") or article.get("link")
    if not url:
        return article
    # Preferred path: Zendesk Help Center API for Ledger
    if _is_ledger_support(url):
        host = "support.ledger.com"
        aid = _extract_article_id(url)
        data = None
        if aid:
            data = _zd_article_by_id(host, aid)
        if not data or not data.get("article"):
            # Fall back to search by title if available
            q = article.get("title") or url.rsplit("/", 1)[-1].replace("-", " ")
            res = _zd_search_article(host, q)
            items = (res or {}).get("results", [])
            # Choose the one whose html_url path matches best with given URL or title
            if items:
                # Prefer exact html_url domain/path containing the slug or id
                chosen = None
                for it in items:
                    if aid and str(it.get("id")) == str(aid):
                        chosen = it
                        break
                    if url and it.get("html_url") and it["html_url"].split("/")[-1][:50] in url:
                        chosen = it
                        break
                if not chosen:
                    chosen = items[0]
                # Wrap into article-like structure
                data = {"article": chosen}
        if data and data.get("article"):
            art = data["article"]
            # Title
            if not article.get("title"):
                article["title"] = art.get("title", "")
            # Dates
            created = art.get("created_at") or art.get("updated_at") or ""
            updated = art.get("updated_at") or ""
            article["publish_date"] = created[:10] if created else article.get("publish_date", "")
            if updated:
                article["updated"] = updated[:10]
            # Topic via section
            sec_id = art.get("section_id")
            if sec_id:
                try:
                    topic_name = _zd_section_name(host, int(sec_id))
                except Exception:
                    topic_name = ""
                if topic_name:
                    article["topic"] = topic_name
            # Summary: from body (HTML) → first 2-3 sentences
            body_html = art.get("body", "")
            if body_html:
                body_text = BeautifulSoup(body_html, "html.parser").get_text(" ", strip=True)
                # Split by sentences roughly
                sentences = re.split(r"(?<=[.!?])\s+", body_text)
                article["summary"] = " ".join(sentences[:3])[:1000]
            # Keywords
            keywords = load_keywords()
            if keywords and (art.get("body") or art.get("title")):
                all_text = f"{art.get('title','')} {BeautifulSoup(art.get('body',''), 'html.parser').get_text(' ', strip=True)}"
                article["keywords"] = _count_keywords(all_text, keywords)
            return article

    # Fallback: HTML scraping
    soup = fetch_page(url)
    if not soup:
        return article

    # Title fallback
    if not article.get("title"):
        h1 = soup.find("h1")
        if h1:
            article["title"] = h1.get_text(strip=True)

    pub, mod = _extract_dates(soup)
    if pub:
        article["publish_date"] = pub
    if mod:
        article["updated"] = mod

    topic = _extract_topic(soup)
    if topic:
        article["topic"] = topic

    summary = _extract_summary(soup)
    article["summary"] = summary

    # Keywords
    keywords = load_keywords()
    if keywords:
        all_text = soup.get_text(" ", strip=True)
        article["keywords"] = _count_keywords(all_text, keywords)

    return article


# =======================
# Save to CSV
# =======================
def save_to_csv(articles):
    ts = datetime.now().strftime("%m%d%y")
    out = os.path.join(OUTPUT_DIR, f"helpcenter_articles_{ts}.csv")
    headers = ["Title", "Publish Date", "Topic", "Summary", "URL"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for a in articles:
            writer.writerow({
                "Title": a.get("title", ""),
                "Publish Date": a.get("publish_date", ""),
                "Topic": a.get("topic", ""),
                "Summary": a.get("summary", ""),
                "URL": a.get("url") or a.get("link", ""),
            })
    print(f"✅ Data saved to {out}")


# =======================
# Main orchestration
# =======================
def run_helpcenter_scrape():
    articles = load_and_sync_articles()
    if not articles:
        print("⚠️ No articles found to scrape. Ensure CSV has rows and correct headers (Title, URL).")
        # Still write empty CSV with header for transparency
        save_to_csv([])
        return
    for i, a in enumerate(articles, 1):
        print(f"Scraping {i}/{len(articles)}: {a.get('url')}")
        updated = scrape_article(a)
        articles[i-1] = updated
    # Persist
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    save_to_csv(articles)
    print("✅ Help Center scrape complete")
