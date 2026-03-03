"""
Async Jira Cloud REST API v3 client for 3 Amigos.

Provides issue reading, creation, commenting, and status transitions.
All functions degrade gracefully if Jira env vars are not configured —
they log a warning and return an error dict / no-op rather than raising.

Requires: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN (all in .env)
Optional: JIRA_PROJECT_KEY (needed for create_issue)
"""
from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from config import JIRA_API_TOKEN, JIRA_EMAIL, JIRA_PROJECT_KEY, JIRA_URL

logger = logging.getLogger(__name__)


# ── Configuration helpers ──────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if the minimum Jira env vars are set."""
    return bool(JIRA_URL and JIRA_EMAIL and JIRA_API_TOKEN)


def _headers() -> dict[str, str]:
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base_url() -> str:
    url = JIRA_URL.rstrip("/")
    if not url.startswith("http"):
        url = f"https://{url}"
    return url


# ── ADF (Atlassian Document Format) helpers ────────────────────────────────────

def _text_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text (paragraphs separated by blank lines) to minimal ADF."""
    paragraphs: list[dict] = []
    for para in text.split("\n\n"):
        stripped = para.strip()
        if stripped:
            paragraphs.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": stripped}],
                }
            )
    if not paragraphs:
        paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    return {"type": "doc", "version": 1, "content": paragraphs}


def _adf_to_text(node: dict | None) -> str:
    """Recursively extract plain text from an ADF document node."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_adf_to_text(child) for child in node.get("content", [])]
    block_types = {"paragraph", "heading", "bulletList", "orderedList", "listItem", "blockquote"}
    sep = "\n" if node.get("type") in block_types else " "
    return sep.join(p for p in parts if p)


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_issue(issue_key: str) -> dict[str, str]:
    """
    Fetch a Jira issue by key (e.g., PROJ-123).

    Returns a flat dict:
        key, summary, description, status, type, url

    Returns {"error": "..."} if not configured or the request fails.
    """
    if not is_configured():
        return {"error": "Jira not configured (set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)"}

    url = f"{_base_url()}/rest/api/3/issue/{issue_key}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                url,
                headers=_headers(),
                params={"fields": "summary,description,status,issuetype,priority,labels"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[Jira] get_issue %s → HTTP %s: %s", issue_key, exc.response.status_code, exc.response.text[:200])
        return {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
    except Exception as exc:
        logger.error("[Jira] get_issue %s error: %s", issue_key, exc)
        return {"error": str(exc)}

    fields = data.get("fields", {})
    description_text = _adf_to_text(fields.get("description") or {})

    return {
        "key": data["key"],
        "summary": fields.get("summary", ""),
        "description": description_text,
        "status": (fields.get("status") or {}).get("name", ""),
        "type": (fields.get("issuetype") or {}).get("name", ""),
        "url": f"{_base_url()}/browse/{data['key']}",
    }


async def create_issue(
    summary: str,
    description: str,
    issue_type: str = "Story",
    labels: list[str] | None = None,
) -> dict[str, str]:
    """
    Create a Jira issue in JIRA_PROJECT_KEY.

    Returns {"key": "PROJ-42", "url": "https://..."} or {"error": "..."}.
    """
    if not is_configured():
        return {"error": "Jira not configured (set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)"}
    if not JIRA_PROJECT_KEY:
        return {"error": "JIRA_PROJECT_KEY not set — cannot create tickets"}

    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": _text_to_adf(description),
            "issuetype": {"name": issue_type},
        }
    }
    if labels:
        payload["fields"]["labels"] = labels

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{_base_url()}/rest/api/3/issue",
                headers=_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[Jira] create_issue failed: HTTP %s: %s", exc.response.status_code, exc.response.text[:300])
        return {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
    except Exception as exc:
        logger.error("[Jira] create_issue error: %s", exc)
        return {"error": str(exc)}

    key = data["key"]
    url = f"{_base_url()}/browse/{key}"
    logger.info("[Jira] Created issue %s: %s", key, url)
    return {"key": key, "url": url}


async def add_comment(issue_key: str, comment: str) -> None:
    """
    Add a plain-text comment to a Jira issue.
    Silently no-ops if Jira is not configured or the request fails.
    """
    if not is_configured():
        return
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{_base_url()}/rest/api/3/issue/{issue_key}/comment",
                headers=_headers(),
                json={"body": _text_to_adf(comment)},
            )
            resp.raise_for_status()
        logger.info("[Jira] Comment added to %s", issue_key)
    except Exception as exc:
        logger.warning("[Jira] add_comment %s failed: %s", issue_key, exc)


async def transition_issue(issue_key: str, status_name: str) -> None:
    """
    Transition a Jira issue to a named status (e.g., 'In Progress', 'In Review', 'Done').
    Silently no-ops if the transition doesn't exist or Jira is not configured.
    """
    if not is_configured():
        return
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Fetch available transitions
            resp = await client.get(
                f"{_base_url()}/rest/api/3/issue/{issue_key}/transitions",
                headers=_headers(),
            )
            resp.raise_for_status()
            transitions = resp.json().get("transitions", [])

            match = next(
                (t for t in transitions if t["name"].lower() == status_name.lower()),
                None,
            )
            if not match:
                logger.warning(
                    "[Jira] No transition named '%s' found for %s. Available: %s",
                    status_name,
                    issue_key,
                    [t["name"] for t in transitions],
                )
                return

            await client.post(
                f"{_base_url()}/rest/api/3/issue/{issue_key}/transitions",
                headers=_headers(),
                json={"transition": {"id": match["id"]}},
            )
        logger.info("[Jira] Transitioned %s → '%s'", issue_key, status_name)
    except Exception as exc:
        logger.warning("[Jira] transition_issue %s → '%s' failed: %s", issue_key, status_name, exc)
