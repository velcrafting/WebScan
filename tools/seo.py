import os
from datetime import datetime
from . import google_search, storage


def serp_metadata(queries_file: str, top: int):
    """Fetch metadata for top search results of given queries."""
    queries = storage.load_json(queries_file, [])
    all_results = []
    for q in queries:
        results = google_search.search_google(q)[:top]
        for r in results:
            meta = google_search.fetch_metadata(r['url'])
            meta.update({'query': q, 'url': r['url']})
            all_results.append(meta)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = os.path.join('output', f'serp_metadata_{ts}.json')
    storage.write_json(out_path, all_results)
    return out_path, len(all_results)
