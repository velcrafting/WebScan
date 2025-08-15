import os
from datetime import datetime
from . import google_search, llm_probe, index_tracker, storage


def serp_reddit(queries_file: str, top: int):
    """Collect Reddit results from Google SERP for given queries."""
    queries = storage.load_json(queries_file, [])
    all_results = []
    for q in queries:
        results = google_search.search_google(q)
        reddit_hits = [r for r in results if "reddit.com" in r.get("url", "")][:top]
        for hit in reddit_hits:
            hit["query"] = q
            all_results.append(hit)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'serp_reddit_{ts}.json')
    storage.write_json(out_path, all_results)
    return out_path, len(all_results)


def llm_probe_queries(queries_file: str):
    """Probe LLM providers for references to the supplied queries."""
    queries = storage.load_json(queries_file, [])
    all_results = []
    for q in queries:
        all_results.extend(llm_probe.probe(q))
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'llm_probe_{ts}.json')
    storage.write_json(out_path, all_results)
    return out_path, len(all_results)


def index_check():
    """Check Google indexing for tracked Reddit posts."""
    return index_tracker.check_indexing()