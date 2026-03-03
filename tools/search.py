"""
Web search tool for Archie's research phase.
Supports multiple providers: Tavily, Zenrows, or basic HTTP fetching.
Provider is configured via WEB_SEARCH_PROVIDER environment variable.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from config import (
    WEB_SEARCH_PROVIDER,
    TAVILY_API_KEY,
    ZENROWS_API_KEY,
)


async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using the configured provider and return formatted results.
    Returns a plain-text summary suitable for Claude's context window.

    Supported providers:
    - tavily: AI-powered search API (requires TAVILY_API_KEY)
    - zenrows: Web scraping with JS rendering (requires ZENROWS_API_KEY)
    - basic: Simple HTTP fetching with httpx (no API key needed)
    """
    provider = WEB_SEARCH_PROVIDER.lower()

    if provider == "tavily":
        return await _search_tavily(query, max_results)
    elif provider == "zenrows":
        return await _search_zenrows(query, max_results)
    elif provider == "basic":
        return await _search_basic(query, max_results)
    else:
        return (
            f"[Web search error: Unknown provider '{provider}'. "
            f"Valid options: tavily, zenrows, basic]"
        )


async def _search_tavily(query: str, max_results: int) -> str:
    """Search using Tavily API (AI-powered search)."""
    if not TAVILY_API_KEY:
        return (
            f"[Web search skipped — TAVILY_API_KEY not set. "
            f"Set WEB_SEARCH_PROVIDER to 'basic' or 'zenrows', or add your API key. "
            f"Query: '{query}']"
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

    lines: list[str] = [f"Search results for: '{query}' (via Tavily)\n"]

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


async def _search_zenrows(query: str, max_results: int) -> str:
    """
    Search using Zenrows API (web scraping with JS rendering).

    Zenrows is better for scraping specific URLs or sites that need JS rendering.
    For general search, we'll use Google search and scrape results.
    """
    if not ZENROWS_API_KEY:
        return (
            f"[Web search skipped — ZENROWS_API_KEY not set. "
            f"Set WEB_SEARCH_PROVIDER to 'basic' or 'tavily', or add your API key. "
            f"Query: '{query}']"
        )

    # Use Zenrows to scrape Google search results
    google_url = f"https://www.google.com/search?q={query}&num={max_results}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://api.zenrows.com/v1/",
            params={
                "apikey": ZENROWS_API_KEY,
                "url": google_url,
                "js_render": "true",
                "premium_proxy": "true",
            },
        )
        resp.raise_for_status()
        html = resp.text

    # Parse Google search results
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Google search result divs
    for result_div in soup.select("div.g")[:max_results]:
        title_elem = result_div.select_one("h3")
        link_elem = result_div.select_one("a")
        snippet_elem = result_div.select_one("div.VwiC3b")

        if title_elem and link_elem:
            title = title_elem.get_text()
            url = link_elem.get("href", "")
            snippet = snippet_elem.get_text() if snippet_elem else ""

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet[:400],
            })

    lines: list[str] = [f"Search results for: '{query}' (via Zenrows)\n"]

    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result['title']}")
        lines.append(f"   URL: {result['url']}")
        if result['snippet']:
            lines.append(f"   {result['snippet']}...")
        lines.append("")

    return "\n".join(lines) if lines else "No results found."


async def _search_basic(query: str, max_results: int) -> str:
    """
    Basic search using DuckDuckGo HTML (no API key needed).

    Limited capabilities compared to Tavily or Zenrows, but works without
    any API key. Good for development or low-volume usage.
    """
    # Use DuckDuckGo HTML search (no API key needed)
    ddg_url = "https://html.duckduckgo.com/html/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            ddg_url,
            data={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            },
        )
        resp.raise_for_status()
        html = resp.text

    # Parse DuckDuckGo results
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for result_div in soup.select("div.result")[:max_results]:
        title_elem = result_div.select_one("a.result__a")
        snippet_elem = result_div.select_one("a.result__snippet")

        if title_elem:
            title = title_elem.get_text()
            url = title_elem.get("href", "")
            snippet = snippet_elem.get_text() if snippet_elem else ""

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet[:400],
            })

    lines: list[str] = [f"Search results for: '{query}' (via DuckDuckGo)\n"]

    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result['title']}")
        lines.append(f"   URL: {result['url']}")
        if result['snippet']:
            lines.append(f"   {result['snippet']}...")
        lines.append("")

    return "\n".join(lines) if lines else "No results found."
