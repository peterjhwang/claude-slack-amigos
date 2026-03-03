"""
3 Amigos LangGraph Workflow
===========================
Orchestrates:  Archie → [human gate] → Builder → [human gate] → Eval → [human gate] → Done

How human-in-the-loop works
-----------------------------
Each agent node calls langgraph.types.interrupt() after posting to Slack.
This pauses the graph and persists its full state in the SQLite checkpointer.
When the engineer clicks "Approve" (or reacts 👍, or types "approve" in thread),
main.py calls resume_workflow() which does:

    await graph.ainvoke(Command(resume="approve"), config)

The interrupt() call returns "approve" and the node completes normally,
then the next node starts.

Jira integration
-----------------
If Archie creates a Jira ticket for Builder, its key is stored in `jira_ticket_key`.
Builder reads this from state and updates the Jira ticket with the PR link + comment.

Module-level singletons
------------------------
  slack_client  — AsyncWebClient injected by main.py's lifespan
  graph         — compiled LangGraph graph injected after checkpointer is ready
"""
from __future__ import annotations

import logging
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt
from slack_sdk.web.async_client import AsyncWebClient

from agents.researcher import run_researcher
from agents.coder import run_coder
from agents.evaluator import run_eval
from state.manager import register_agent_message, update_thread_phase
from tools.slack_poster import (
    make_approval_blocks,
    post_as_researcher,
    post_as_coder,
    post_as_evaluator,
)

logger = logging.getLogger(__name__)

# Injected by main.py after startup
slack_client: AsyncWebClient | None = None
graph = None  # CompiledStateGraph


# ── State schema ───────────────────────────────────────────────────────────────

class AmigosState(TypedDict):
    channel_id: str
    thread_ts: str
    task: str
    # Each agent writes its output here; downstream agents read it
    archie_output: Optional[str]
    builder_output: Optional[str]
    eval_output: Optional[str]
    # Timestamps of the approval messages (used for reaction routing)
    archie_msg_ts: Optional[str]
    builder_msg_ts: Optional[str]
    eval_msg_ts: Optional[str]
    # Jira ticket Archie creates for Builder to pick up (None if Jira not configured)
    jira_ticket_key: Optional[str]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _require_client() -> AsyncWebClient:
    if slack_client is None:
        raise RuntimeError("slack_client not initialised — check lifespan setup")
    return slack_client


# ── Nodes ──────────────────────────────────────────────────────────────────────

async def archie_node(state: AmigosState) -> dict:
    """
    1. Post "starting" ack to Slack
    2. Run Archie's research + architecture design
    3. Post full output (auto-chunked for long messages)
    4. Post Jira ticket notification (if created)
    5. Post approval buttons as a follow-up message
    6. interrupt() — pauses until engineer approves
    """
    client = _require_client()
    channel_id = state["channel_id"]
    thread_ts = state["thread_ts"]
    task = state["task"]

    logger.info("[Archie] Starting for thread %s", thread_ts)

    await post_as_researcher(
        client, channel_id, thread_ts,
        "🔍 *Researching your task...* I'll post the full architecture + spec shortly. "
        "Sit tight — this usually takes 30–60 s.",
    )

    try:
        archie_output, jira_ticket_key = await run_researcher(task)
    except Exception as exc:
        logger.exception("[Archie] Research failed")
        await post_as_researcher(
            client, channel_id, thread_ts,
            f"❌ *Research error:* `{exc}`\nPlease try again or simplify the task.",
        )
        raise

    # Post the architecture (may be split across multiple messages)
    await post_as_researcher(client, channel_id, thread_ts, archie_output)

    # If Archie created a Jira ticket, surface it prominently in Slack
    if jira_ticket_key:
        await post_as_researcher(
            client, channel_id, thread_ts,
            f"🎫 *Jira ticket created for Builder:* `{jira_ticket_key}`\n"
            "_Builder will pick this up and update the ticket with the PR link._",
        )

    # Approval gate message
    approval_blocks = make_approval_blocks(
        "*Archie has completed the architecture!* "
        "React 👍 or click *Approve* to hand off to Builder.",
        "archie",
    )
    approval_ts = await post_as_researcher(
        client, channel_id, thread_ts,
        "✋ *Ready for your sign-off!* Click Approve or react 👍 to this message.",
        blocks=approval_blocks,
    )

    await register_agent_message(approval_ts, thread_ts, channel_id, "archie")
    await update_thread_phase(thread_ts, "waiting_archie_approval")

    # ── Human gate ────────────────────────────────────────────────────────────
    decision = interrupt({"phase": "archie", "msg_ts": approval_ts})
    logger.info("[Archie] Resumed. Decision: %s", decision)

    return {
        "archie_output": archie_output,
        "archie_msg_ts": approval_ts,
        "jira_ticket_key": jira_ticket_key,
    }


async def builder_node(state: AmigosState) -> dict:
    """
    1. Post "starting" ack
    2. Run Builder's agentic loop (Claude Code CLI)
    3. Post build summary + PR link
    4. Update Jira ticket with PR link + transition to In Review (if configured)
    5. Post approval buttons
    6. interrupt() — pauses until engineer approves
    """
    client = _require_client()
    channel_id = state["channel_id"]
    thread_ts = state["thread_ts"]
    task = state["task"]
    archie_output = state["archie_output"] or ""
    jira_ticket_key = state.get("jira_ticket_key")

    logger.info("[Builder] Starting for thread %s (jira=%s)", thread_ts, jira_ticket_key)

    await post_as_coder(
        client, channel_id, thread_ts,
        "🔨 *Building based on Archie's architecture...*\n"
        "I have bash + file access — actually writing and running code now. "
        "Progress updates every 5 operations.",
    )
    await update_thread_phase(thread_ts, "building")

    # Progress updates are posted back into the same thread
    async def _progress(msg: str) -> None:
        await post_as_coder(client, channel_id, thread_ts, msg)

    try:
        builder_output, pr_url = await run_coder(
            task,
            archie_output,
            build_id=thread_ts,           # isolated sandbox per thread
            progress_callback=_progress,
            jira_ticket_key=jira_ticket_key,
        )
    except Exception as exc:
        logger.exception("[Builder] Build failed")
        await post_as_coder(
            client, channel_id, thread_ts,
            f"❌ *Build error:* `{exc}`\nCheck logs and retry.",
        )
        raise

    # Post the build summary
    await post_as_coder(client, channel_id, thread_ts, builder_output)

    # Post the PR link as a prominent standalone message (or a note if no PR)
    if pr_url:
        await post_as_coder(
            client, channel_id, thread_ts,
            f"🔗 *Pull Request opened:*\n{pr_url}\n\n"
            "_Review the code on GitHub, then come back here to approve Eval._",
        )
    else:
        await post_as_coder(
            client, channel_id, thread_ts,
            "ℹ️ _No GITHUB_REPO configured — code was built locally. "
            "Set `GITHUB_TOKEN` + `GITHUB_REPO` in `.env` to get automatic PRs._",
        )

    approval_blocks = make_approval_blocks(
        "*Builder has completed the implementation!* "
        "React 👍 or click *Approve* to send to Eval.",
        "builder",
    )
    approval_ts = await post_as_coder(
        client, channel_id, thread_ts,
        "✋ *Implementation complete!* Approve to run Eval, or request changes.",
        blocks=approval_blocks,
    )

    await register_agent_message(approval_ts, thread_ts, channel_id, "builder")
    await update_thread_phase(thread_ts, "waiting_builder_approval")

    # ── Human gate ────────────────────────────────────────────────────────────
    decision = interrupt({"phase": "builder", "msg_ts": approval_ts})
    logger.info("[Builder] Resumed. Decision: %s", decision)

    return {
        "builder_output": builder_output,
        "builder_msg_ts": approval_ts,
    }


async def eval_node(state: AmigosState) -> dict:
    """
    1. Post "starting" ack
    2. Run Eval (LLM-as-judge + red-teaming)
    3. Post evaluation report
    4. Post approval buttons for final sign-off
    5. interrupt() — pauses until engineer signs off
    """
    client = _require_client()
    channel_id = state["channel_id"]
    thread_ts = state["thread_ts"]
    task = state["task"]
    archie_output = state["archie_output"] or ""
    builder_output = state["builder_output"] or ""

    logger.info("[Eval] Starting for thread %s", thread_ts)

    await post_as_evaluator(
        client, channel_id, thread_ts,
        "📊 *Running evaluations & red-team testing...* "
        "Checking all acceptance criteria. Back shortly!",
    )
    await update_thread_phase(thread_ts, "evaluating")

    try:
        eval_output = await run_eval(task, archie_output, builder_output)  # archie_output used as researcher_spec
    except Exception as exc:
        logger.exception("[Eval] Eval failed")
        await post_as_evaluator(
            client, channel_id, thread_ts,
            f"❌ *Eval error:* `{exc}`\nCheck logs.",
        )
        raise

    await post_as_evaluator(client, channel_id, thread_ts, eval_output)

    approval_blocks = make_approval_blocks(
        "*Eval has completed testing!* "
        "React 👍 or click *Approve* for final sign-off.",
        "eval",
    )
    approval_ts = await post_as_evaluator(
        client, channel_id, thread_ts,
        "✋ *Eval complete!* Final sign-off to wrap up the mission.",
        blocks=approval_blocks,
    )

    await register_agent_message(approval_ts, thread_ts, channel_id, "eval")
    await update_thread_phase(thread_ts, "waiting_eval_approval")

    # ── Human gate (final sign-off) ───────────────────────────────────────────
    decision = interrupt({"phase": "eval", "msg_ts": approval_ts})
    logger.info("[Eval] Resumed. Final decision: %s", decision)

    return {
        "eval_output": eval_output,
        "eval_msg_ts": approval_ts,
    }


async def summary_node(state: AmigosState) -> dict:
    """Post the tri-agent closing summary, close Jira ticket, mark thread done."""
    client = _require_client()
    channel_id = state["channel_id"]
    thread_ts = state["thread_ts"]
    jira_ticket_key = state.get("jira_ticket_key")

    await post_as_researcher(client, channel_id, thread_ts, "✅ Architecture locked and approved.")
    await post_as_coder(client, channel_id, thread_ts, "✅ Code complete and approved.")
    await post_as_evaluator(
        client, channel_id, thread_ts,
        "✅ Evals passed and approved. Mission accomplished! 🚀",
    )

    jira_line = (
        f"\n• 🎫 *Jira `{jira_ticket_key}` transitioned to Done*"
        if jira_ticket_key
        else ""
    )

    final = (
        "---\n"
        "*✅ 3 Amigos — Mission Complete!*\n\n"
        "• 🧠 *Architecture locked* — Archie's spec approved\n"
        "• 🔨 *Code complete* — Builder's implementation approved\n"
        f"• 📊 *Evals passed* — Eval's sign-off granted{jira_line}\n\n"
        "_Ready for your final deployment. React 👍 or ping us with a new task!_"
    )
    await post_as_researcher(client, channel_id, thread_ts, final)
    await update_thread_phase(thread_ts, "done")

    # Transition Jira ticket to Done
    if jira_ticket_key:
        from tools import jira_client
        await jira_client.transition_issue(jira_ticket_key, "Done")

    return {}


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph(checkpointer) -> object:
    """
    Compile the 3 Amigos LangGraph with SQLite checkpointing.
    The checkpointer persists interrupted state so resume_workflow() works
    even after a server restart.
    """
    sg = StateGraph(AmigosState)

    sg.add_node("archie", archie_node)
    sg.add_node("builder", builder_node)
    sg.add_node("eval", eval_node)
    sg.add_node("summary", summary_node)

    sg.set_entry_point("archie")
    sg.add_edge("archie", "builder")
    sg.add_edge("builder", "eval")
    sg.add_edge("eval", "summary")
    sg.add_edge("summary", END)

    return sg.compile(checkpointer=checkpointer)


# ── Public control functions (called from main.py) ─────────────────────────────

async def start_workflow(task: str, channel_id: str, thread_ts: str) -> None:
    """Kick off a fresh 3 Amigos workflow. thread_ts is used as the LangGraph thread_id."""
    config = {"configurable": {"thread_id": thread_ts}}
    initial_state: AmigosState = {
        "channel_id": channel_id,
        "thread_ts": thread_ts,
        "task": task,
        "archie_output": None,
        "builder_output": None,
        "eval_output": None,
        "archie_msg_ts": None,
        "builder_msg_ts": None,
        "eval_msg_ts": None,
        "jira_ticket_key": None,
    }
    try:
        await graph.ainvoke(initial_state, config)
    except Exception:
        logger.exception("Workflow failed for thread %s", thread_ts)


async def resume_workflow(thread_ts: str, decision: str = "approve") -> None:
    """
    Resume a paused workflow after human approval.
    `decision` is the value returned by interrupt() in the node.
    Typically "approve" or "changes:<text>".
    """
    config = {"configurable": {"thread_id": thread_ts}}
    try:
        await graph.ainvoke(Command(resume=decision), config)
    except Exception:
        logger.exception("Resume failed for thread %s", thread_ts)
