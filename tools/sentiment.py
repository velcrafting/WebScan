POSITIVE = {"good", "great", "safe", "secure", "positive", "helpful"}
NEGATIVE = {"bad", "unsafe", "scam", "risk", "negative", "hack", "problem"}

def score(text: str) -> int:
    text = (text or "").lower()
    s = 0
    for w in POSITIVE:
        if w in text:
            s += 1
    for w in NEGATIVE:
        if w in text:
            s -= 1
    return s

def tone(score_value: int) -> str:
    if score_value > 0:
        return "positive"
    if score_value < 0:
        return "negative"
    return "neutral"

def tone_from_text(text: str) -> str:
    return tone(score(text))