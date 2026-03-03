"""
Slack posting utilities for the 3 Amigos agents.
Each agent posts with its own username + emoji so messages look distinct in Slack.
Handles long messages by splitting them into chunks (Slack's 3 000 char limit).
"""
from __future__ import annotations

from slack_sdk.web.async_client import AsyncWebClient

from config import RESEARCHER_PERSONA, CODER_PERSONA, EVALUATOR_PERSONA

# Slack Block Kit section text limit (hard limit is 3 000; we keep a buffer)
_CHUNK_LIMIT = 2_800


def _chunk_text(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
    """Split text into Slack-safe chunks, breaking on newlines where possible."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


async def post_as(
    client: AsyncWebClient,
    channel: str,
    thread_ts: str,
    text: str,
    persona: dict,
    blocks: list | None = None,
) -> str:
    """
    Post a message with a custom agent persona.
    Returns the ts of the last posted message (used for reaction tracking).
    """
    # Long text without blocks → split into multiple messages
    if not blocks and len(text) > _CHUNK_LIMIT:
        chunks = _chunk_text(text)
        last_ts = thread_ts
        for i, chunk in enumerate(chunks):
            label = f"\n\n_Part {i + 1}/{len(chunks)}_" if len(chunks) > 1 else ""
            resp = await client.chat_postMessage(
                channel=channel,
                text=chunk + label,
                thread_ts=thread_ts,
                username=persona["username"],
                icon_emoji=persona["icon_emoji"],
            )
            last_ts = resp["ts"]
        return last_ts

    resp = await client.chat_postMessage(
        channel=channel,
        text=text,
        thread_ts=thread_ts,
        username=persona["username"],
        icon_emoji=persona["icon_emoji"],
        **({"blocks": blocks} if blocks else {}),
    )
    return resp["ts"]


async def post_as_researcher(
    client: AsyncWebClient,
    channel: str,
    thread_ts: str,
    text: str,
    blocks: list | None = None,
) -> str:
    return await post_as(client, channel, thread_ts, text, RESEARCHER_PERSONA, blocks)


async def post_as_coder(
    client: AsyncWebClient,
    channel: str,
    thread_ts: str,
    text: str,
    blocks: list | None = None,
) -> str:
    return await post_as(client, channel, thread_ts, text, CODER_PERSONA, blocks)


async def post_as_evaluator(
    client: AsyncWebClient,
    channel: str,
    thread_ts: str,
    text: str,
    blocks: list | None = None,
) -> str:
    return await post_as(client, channel, thread_ts, text, EVALUATOR_PERSONA, blocks)


def make_approval_blocks(prompt_text: str, phase: str) -> list:
    """
    Build a Block Kit message with Approve / Request Changes buttons.
    `phase` is used to namespace action_ids (e.g. "archie", "builder", "eval").
    """
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": prompt_text},
        },
        {
            "type": "actions",
            "block_id": f"approval_{phase}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👍 Approve", "emoji": True},
                    "style": "primary",
                    "action_id": f"approve_{phase}",
                    "value": "approve",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Request Changes",
                        "emoji": True,
                    },
                    "style": "danger",
                    "action_id": f"changes_{phase}",
                    "value": "changes",
                },
            ],
        },
    ]
