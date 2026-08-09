"""Tavily web search — live hours, weather, transit, current conditions."""
from __future__ import annotations

import httpx

from app import config


def web_search(query: str, max_results: int = 4) -> str:
    if not config.TAVILY_API_KEY:
        return "Web search is not configured."
    r = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": config.TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    parts = []
    if data.get("answer"):
        parts.append(f"Summary: {data['answer']}")
    for item in data.get("results", []):
        parts.append(f"- {item['title']}: {item['content'][:300]} ({item['url']})")
    return "\n".join(parts) or "No results."
