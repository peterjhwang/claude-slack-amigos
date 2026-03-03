"""
Web search tool for Archie's research phase.
Uses Tavily API — free tier is sufficient for development.
Falls back gracefully if TAVILY_API_KEY is not configured.
"""
from __future__ import annotations

import httpx
from config import TAVILY_API_KEY


async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web via Tavily and return formatted results.
    Returns a plain-text summary suitable for Claude's context window.
    """
    if not TAVILY_API_KEY:
        return (
            f"[Web search skipped — TAVILY_API_KEY not set. "
            f"Answering from training knowledge for query: '{query}']"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    lines: list[str] = [f"Search results for: '{query}'\n"]

    if data.get("answer"):
        lines.append(f"Summary: {data['answer']}\n")

    for i, result in enumerate(data.get("results", []), 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        content = result.get("content", "")[:400].replace("\n", " ")
        lines.append(f"{i}. {title}")
        lines.append(f"   URL: {url}")
        lines.append(f"   {content}...")
        lines.append("")

    return "\n".join(lines) if lines else "No results found."
