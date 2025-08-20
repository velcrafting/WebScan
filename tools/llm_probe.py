from datetime import datetime
import re
from urllib.parse import urlparse

from . import llm_connector, sentiment
import config


def probe(query: str):
    results = []
    providers = config.LLM_PROVIDERS
    for name, cfg in providers.items():
        answer = llm_connector.query(name, query, cfg)

        lower_answer = answer.lower()

        tone = sentiment.tone_from_text(answer)
        cites_reddit = "reddit.com" in lower_answer
        cites_ledger = "ledger" in lower_answer

        reddit_links = re.findall(r"https?://(?:www\\.)?reddit\\.com[^\\s)\"'<>]*", lower_answer)
        subreddits = []
        for link in reddit_links:
            try:
                path = urlparse(link).path
                parts = path.split('/')
                if len(parts) > 2 and parts[1] == 'r':
                    subreddits.append(parts[2])
            except ValueError:
                continue

        results.append({
            "run_ts": datetime.utcnow().isoformat(),
            "query": query,
            "provider": name,
            "cites_reddit": cites_reddit,
            "cites_ledger": cites_ledger,
            "tone": tone,
            "reddit_links": reddit_links,
            "subreddits": list(set(subreddits)),
            "excerpt": answer[:280],
        })
    return results
