import csv
import json
import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')

def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def write_csv(path, rows, headers=None):
    _ensure_dir(path)
    if not rows:
        open(path, 'w').close()
        return
    headers = headers or list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

def write_json(path, data):
    _ensure_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default if default is not None else []

def write_run_summary(lines):
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    path = os.path.join(OUTPUT_DIR, f'run_summary_{ts}.txt')
    _ensure_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def append_csv(path, row, headers):
    _ensure_dir(path)
    file_exists = os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_csv(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return []