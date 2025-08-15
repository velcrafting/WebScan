from datetime import datetime
from . import sentiment
import config


def probe(query: str):
    results = []
    providers = config.LLM_PROVIDERS
    for name, cfg in providers.items():
        api_key = cfg.get("api_key")
        if not api_key:
            answer = "No API key provided."
        else:
            # Placeholder for real API calls
            answer = "Stubbed response from LLM."
        tone = sentiment.tone_from_text(answer)
        cites_reddit = "reddit.com" in answer.lower()
        cites_ledger = "ledger.com" in answer.lower()
        results.append({
            "run_ts": datetime.utcnow().isoformat(),
            "query": query,
            "provider": name,
            "cites_reddit": cites_reddit,
            "cites_ledger": cites_ledger,
            "tone": tone,
            "excerpt": answer[:280],
        })
    return results
