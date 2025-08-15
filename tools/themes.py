import json

def load_rules(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def classify(text: str, rules: dict) -> str:
    text_l = (text or '').lower()
    for theme, keywords in rules.items():
        for kw in keywords:
            if kw.lower() in text_l:
                return theme
    return None