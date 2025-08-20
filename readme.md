# Web-Scan

## Overview

**web-scan** is a comprehensive Python script stack designed to automate and streamline the extraction and analysis of information from various online platforms including Google, YouTube, Reddit, and specific web sources. It's particularly suited for researchers, social media analysts, content creators, and anyone needing automated web scraping with customizable parameters.

---

## Directory Structure

```
web-scan/
├── data/
│   ├── keywords.json
│   └── websites.json
├── input/
│   └── academy_content.json
├── output/
│   ├── youtube_comments_(video ID)/
│   ├── youtube_comments_(Channel ID)/
│   └── web_scraping_results.csv
├── tools/
│   ├── __init__.py
│   ├── academy_search.py
│   ├── google_search.py
│   ├── reddit_search.py
│   └── youtube_search.py
├── config.example.py
├── requirements.txt
├── tree.txt
├── main.py
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Required Python libraries installed via `requirements.txt`:

```bash
pip install -r requirements.txt
```

- **Important:** Rename `config.example.py` to `config.py` and replace the placeholder values with your actual API credentials for Google, YouTube, and Reddit.

---

## Usage

Run the script using:

```bash
python main.py
```

This will launch an interactive menu, allowing you to select from various scraping tasks.

---

## Configuration Files

The `/data` directory contains configuration JSON files:

- **keywords.json**: Contains a list of keywords used across different scraping modules.
- **websites.json**: Stores websites for targeted Google searches.

The root directory contains:

- **config.example.py**: Template configuration file. Rename to `config.py` and input your credentials.

---

## Tools Overview

### 1. Google Search

The **Google Search** tool performs automated Google searches using the Google Custom Search API. It:

- Searches using specified keywords and websites.
- Extracts detailed metadata such as title, description, publication date, last edit date, and author from search results.
- Stores search results in organized CSV files, timestamped for easy reference.
- Implements randomized delays to mimic human browsing and avoid detection.

*Note: Requires Google API credentials configured in `config.py`.*

### 2. YouTube Search

The **YouTube Search** tool leverages the YouTube Data API to automate comment extraction from videos and channels. It:

- Fetches comments from specified YouTube videos, optionally filtered by predefined keywords or retrieved in raw mode (all comments).
- Extracts comprehensive metadata for comments, including likes, reply counts, and influencer engagement.
- Allows for channel-wide searches to gather comments across multiple videos within a channel.
- Outputs structured data to clearly labeled CSV files, facilitating efficient data analysis.

*Ensure YouTube API credentials are properly configured in `config.py`.*

### 3. Reddit Search

The **Reddit Search** tool uses the PRAW (Python Reddit API Wrapper) to perform automated searches on Reddit. It:

- Conducts searches using specified keywords across Reddit posts sorted by "new" and "top."
- Extracts detailed post metadata, including title, subreddit, content, author information, flair, upvote counts, and comments.
- Retrieves and formats the top comments for each post.
- Outputs the data to CSV files, labeled clearly by date for ease of analysis.

*Ensure Reddit API credentials (client ID, client secret) are properly set in your configuration.*

### 4. Academy Search (Beta)

*Currently in beta development stage.*

The **Academy Search** tool is designed to scrape articles from the Ledger Academy website. It can:

- Discover and scrape articles directly from the Ledger Academy homepage.
- Import articles from CSV files for targeted scraping.
- Extract key details such as title, description, publish date, and last edit date.
- Check availability of translated articles across multiple languages.

Please note this tool is actively being developed and may experience updates or changes in functionality.

---

## Output

Scraped data outputs to organized files within the `/output` directory. Each search tool has its own output conventions clearly labeled for ease of identification and analysis.

---

## Dependencies

- Requests
- BeautifulSoup
- Google API Client
- PRAW (Python Reddit API Wrapper)
- pandas
- googleapiclient

---

## Contributing

Feel free to contribute by submitting pull requests or opening issues to suggest enhancements or report bugs.

---

## License

```plaintext
MIT License
```

---