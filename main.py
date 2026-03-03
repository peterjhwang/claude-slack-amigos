"""
3 Amigos Slack Bot — Entry Point
==================================
Single @amigos bot that routes all events through Slack Bolt + FastAPI.
Three AI agents (Archie, Builder, Eval) are internal roles that post with
custom usernames so they look distinct in Slack.

Approval triggers (any of these resumes the paused LangGraph workflow):
  • Click the "👍 Approve" Block Kit button
  • React 👍 (+1) to the agent's approval message
  • Type "approve", "lgtm", "ship it", or "yes" in the thread

Changes request:
  • Click "✏️ Request Changes" button  (bot will ask for details)
  • Type "changes: <description>" in the thread
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_sdk.web.async_client import AsyncWebClient

import config
import workflow
from state.manager import (
    create_thread_state,
    get_thread_by_msg_ts,
    get_thread_state,
    init_db,
)
from tools import jira_client
from tools.slack_poster import post_as_archie

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Regex to detect a bare Jira ticket key like "PROJ-123" or "ABC-42"
_JIRA_KEY_RE = re.compile(r"^([A-Z][A-Z0-9]+-\d+)$")

# ── Slack App ──────────────────────────────────────────────────────────────────
slack_app = AsyncApp(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)


# ── FastAPI lifespan (startup / shutdown) ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 3 Amigos starting up...")

    # 1. Initialise the application state DB
    await init_db()

    # 2. Inject the Slack client into the workflow module
    workflow.slack_client = AsyncWebClient(token=config.SLACK_BOT_TOKEN)

    # 3. Build the LangGraph with a persistent SQLite checkpointer.
    #    We keep the context manager alive for the entire app lifetime so
    #    the checkpointer stays open and can resume interrupted workflows.
    os.makedirs(os.path.dirname(os.path.abspath(config.CHECKPOINT_DB)), exist_ok=True)

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError:  # pragma: no cover
        from langgraph_checkpoint_sqlite import AsyncSqliteSaver  # type: ignore[no-redef]

    async with AsyncSqliteSaver.from_conn_string(config.CHECKPOINT_DB) as checkpointer:
        workflow.graph = workflow.build_graph(checkpointer)
        logger.info("✅ 3 Amigos ready! Send @amigos <task> in any channel.")
        yield  # ← server is running here

    logger.info("👋 3 Amigos shut down.")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="3 Amigos Slack Bot",
    description="AI engineering team: Archie (Architect), Builder (Coder), Eval (Evaluator)",
    version="1.0.0",
    lifespan=lifespan,
)

handler = AsyncSlackRequestHandler(slack_app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "3-amigos"}


@app.post("/slack/events")
async def slack_events(req: Request):
    """Handles Slack Event Subscriptions (app_mention, reaction_added, message)."""
    return await handler.handle(req)


@app.post("/slack/interactive")
async def slack_interactive(req: Request):
    """Handles Block Kit button clicks and other interactive payloads."""
    return await handler.handle(req)


# ── Event: @amigos mention ─────────────────────────────────────────────────────
@slack_app.event("app_mention")
async def handle_mention(event: dict, client: AsyncWebClient):
    """
    Triggered when someone writes @amigos <task>.
    Starts a new 3 Amigos workflow in the message's thread.
    """
    channel_id: str = event["channel"]
    event_ts: str = event["ts"]
    thread_ts: str = event.get("thread_ts", event_ts)  # use existing thread or start one
    text: str = event.get("text", "")

    # Strip the bot mention tag(s)
    task = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    # If the task is just a Jira ticket key (e.g., @amigos PROJ-123),
    # auto-fetch the ticket description and use it as the task.
    jira_match = _JIRA_KEY_RE.match(task)
    if jira_match:
        ticket_key = jira_match.group(1).upper()
        issue = await jira_client.get_issue(ticket_key)
        if "error" not in issue:
            await post_as_archie(
                client, channel_id, thread_ts,
                f"📋 *Loaded Jira ticket {ticket_key}:* {issue['summary']}\n{issue['url']}",
            )
            task = f"[{ticket_key}] {issue['summary']}\n\n{issue['description']}"
        else:
            await post_as_archie(
                client, channel_id, thread_ts,
                f"⚠️ Could not load Jira ticket `{ticket_key}`: {issue['error']}\n"
                "Treating it as a plain task description.",
            )

    if not task:
        await post_as_archie(
            client, channel_id, thread_ts,
            "👋 *Hey! I'm the 3 Amigos bot.*\n\n"
            "Give me a task and the whole team will handle it:\n"
            "  1️⃣ 🧠 *Archie* — researches & designs the architecture\n"
            "  2️⃣ 🔨 *Builder* — implements it (after your 👍)\n"
            "  3️⃣ 📊 *Eval* — tests & red-teams it (after your 👍)\n\n"
            "*Example:* `@amigos Build a RAG pipeline with Claude + Pinecone for PDF Q&A`",
        )
        return

    # Guard: don't start a second workflow in the same thread
    existing = await get_thread_state(thread_ts)
    if existing and existing["phase"] not in ("done", "error"):
        await post_as_archie(
            client, channel_id, thread_ts,
            f"⚠️ There's already an active workflow in this thread "
            f"(phase: `{existing['phase']}`). "
            "Approve the current phase or start a new thread for a new task.",
        )
        return

    logger.info("New task received: %s", task[:120])

    # Persist thread state and post welcome
    await create_thread_state(thread_ts, channel_id, task)

    await post_as_archie(
        client, channel_id, thread_ts,
        f"🎯 *3 Amigos on it!* Task received:\n\n_{task}_\n\n"
        "Here's the plan:\n"
        "  1️⃣ 🧠 *Archie* will research & design the architecture\n"
        "  2️⃣ 🔨 *Builder* will implement it (after your 👍)\n"
        "  3️⃣ 📊 *Eval* will test & red-team it (after your 👍)\n\n"
        "Kicking off now...",
    )

    # Fire-and-forget — the workflow runs async while Bolt's ack goes back to Slack
    asyncio.create_task(
        workflow.start_workflow(task, channel_id, thread_ts)
    )


# ── Event: 👍 reaction added ───────────────────────────────────────────────────
@slack_app.event("reaction_added")
async def handle_reaction_added(event: dict):
    """Resume the paused workflow when someone reacts 👍 to an agent's message."""
    if event.get("reaction") != "+1":
        return

    item = event.get("item", {})
    if item.get("type") != "message":
        return

    msg_ts: str = item["ts"]
    info = await get_thread_by_msg_ts(msg_ts)
    if not info:
        return  # Reaction is on a non-amigos message

    logger.info("👍 reaction on %s's message → resuming thread %s", info["agent"], info["thread_ts"])
    asyncio.create_task(workflow.resume_workflow(info["thread_ts"], "approve"))


# ── Action: 👍 Approve button ──────────────────────────────────────────────────
@slack_app.action(re.compile(r"approve_.*"))
async def handle_approve_button(ack, body: dict, client: AsyncWebClient):
    """Resume the workflow when the engineer clicks the Approve button."""
    await ack()

    action = body["actions"][0]
    phase = action["action_id"].replace("approve_", "")

    message: dict = body.get("message", {})
    # Approval message is inside a thread — use thread_ts to identify the workflow
    thread_ts: str | None = message.get("thread_ts") or message.get("ts")
    channel_id: str = body["container"]["channel_id"]

    if not thread_ts:
        logger.warning("Could not extract thread_ts from button body")
        return

    logger.info("✅ Approve clicked for phase=%s thread=%s", phase, thread_ts)

    # Update the button message to remove clickable buttons (avoid double-clicks)
    try:
        await client.chat_update(
            channel=channel_id,
            ts=message["ts"],
            text=f"✅ *{phase.capitalize()} approved!* Proceeding...",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *{phase.capitalize()} approved!* Proceeding...",
                    },
                }
            ],
        )
    except Exception as exc:
        logger.warning("Could not update button message: %s", exc)

    asyncio.create_task(workflow.resume_workflow(thread_ts, "approve"))


# ── Action: ✏️ Request Changes button ─────────────────────────────────────────
@slack_app.action(re.compile(r"changes_.*"))
async def handle_changes_button(ack, body: dict, client: AsyncWebClient):
    """Ask the engineer to describe what they want changed."""
    await ack()

    action = body["actions"][0]
    phase = action["action_id"].replace("changes_", "")

    message: dict = body.get("message", {})
    thread_ts: str | None = message.get("thread_ts") or message.get("ts")
    channel_id: str = body["container"]["channel_id"]

    logger.info("✏️ Changes requested for phase=%s thread=%s", phase, thread_ts)

    try:
        await client.chat_update(
            channel=channel_id,
            ts=message["ts"],
            text=f"✏️ *Changes requested for {phase}.*",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"✏️ *Changes requested for {phase.capitalize()}.*\n\n"
                            "Please reply in this thread with your changes, starting with `changes:` —\n"
                            "_e.g.,_ `changes: Use PostgreSQL instead of SQLite and add Redis caching`"
                        ),
                    },
                }
            ],
        )
    except Exception as exc:
        logger.warning("Could not update button message: %s", exc)


# ── Event: thread messages (keyword-based approval / changes) ──────────────────
@slack_app.event("message")
async def handle_thread_message(event: dict):
    """
    Parse thread replies for approval keywords or "changes: ..." instructions.
    Ignores bot messages and top-level (non-thread) messages.
    """
    # Ignore bot posts and message edits/deletes
    if event.get("bot_id") or event.get("subtype"):
        return

    thread_ts: str | None = event.get("thread_ts")
    if not thread_ts:
        return  # Top-level message — ignore

    text = (event.get("text") or "").strip().lower()

    # Check if there's an active amigos workflow in this thread
    state = await get_thread_state(thread_ts)
    if not state or state["phase"] in ("done", "error"):
        return

    # Keywords that mean "approve"
    APPROVE_KEYWORDS = {"approve", "approved", "👍", "lgtm", "ship it", "yes", "+1", ":+1:"}
    if text in APPROVE_KEYWORDS:
        logger.info("Approve keyword '%s' in thread %s", text, thread_ts)
        asyncio.create_task(workflow.resume_workflow(thread_ts, "approve"))
        return

    # "changes: <description>" → pass description back to the interrupted node
    if text.startswith("changes:"):
        changes_text = text[len("changes:"):].strip()
        logger.info("Changes '%s' in thread %s", changes_text[:80], thread_ts)
        asyncio.create_task(workflow.resume_workflow(thread_ts, f"changes:{changes_text}"))
