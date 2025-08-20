"""Utility functions to query various LLM providers."""
from typing import Dict

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency might be missing at runtime
    OpenAI = None  # type: ignore


def query(provider: str, prompt: str, cfg: Dict[str, str]) -> str:
    """Query the specified LLM provider and return the response text."""
    api_key = cfg.get("api_key")
    if not api_key:
        return "No API key provided."

    if provider == "chatgpt" and OpenAI:
        model = cfg.get("model", "gpt-3.5-turbo")
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message["content"].strip()
        except Exception as exc:  # pragma: no cover - network/remote errors
            return f"Error querying {provider}: {exc}"
    return f"Unsupported provider: {provider}"
