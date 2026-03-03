"""
Archie — AI Architect & Researcher
====================================
Default mode:  LangGraph `create_react_agent` (prebuilt ReAct loop)
Optional mode: Claude Code CLI subprocess (set ARCHIE_USE_CLAUDE_CODE=true)

ReAct loop (default)
---------------------
Archie reasons and acts in a loop:
  Think → web_search / read_jira_ticket → think → … → draft architecture

create_react_agent wires up:
  - ChatAnthropic model (tool-calling)
  - Tools: web_search [always], read_jira_ticket + create_jira_ticket [if configured]
  - System prompt enforcing the output format

Claude Code CLI mode (ARCHIE_USE_CLAUDE_CODE=true)
---------------------------------------------------
Archie delegates to `claude --print` in a temp workspace.
Uses the Claude Max subscription quota instead of direct API tokens.
Good for spec-generation tasks where web research isn't needed.

Return value
------------
`run_archie(task)` always returns:
    (output_text: str, jira_ticket_key: str | None)

jira_ticket_key is the key of the Jira Story Archie created for Builder,
or None if Jira is not configured / Archie didn't create one.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from config import (
    ANTHROPIC_API_KEY,
    ARCHIE_MODEL,
    ARCHIE_USE_CLAUDE_CODE,
    JIRA_API_TOKEN,
    JIRA_EMAIL,
    JIRA_PROJECT_KEY,
    JIRA_URL,
)
from tools import jira_client
from tools.search import web_search as _do_web_search

logger = logging.getLogger(__name__)

_CLAUDE_CODE_TIMEOUT = 300  # 5 min is plenty for spec generation


# ── LangChain tools ────────────────────────────────────────────────────────────

@tool
async def web_search(query: str) -> str:
    """
    Search the web for current information about AI models, tools, frameworks,
    APIs, benchmarks, and pricing. Use this to verify up-to-date choices before
    committing to an architecture recommendation.
    """
    logger.info("[Archie/web_search] query=%s", query[:120])
    return await _do_web_search(query)


@tool
async def read_jira_ticket(ticket_key: str) -> str:
    """
    Read a Jira ticket by its key (e.g., PROJ-123).
    Returns the ticket's summary, description, status, and URL.
    Use this when the task references a Jira ticket key or when you need
    to understand an existing issue before designing the architecture.
    """
    logger.info("[Archie/read_jira_ticket] key=%s", ticket_key)
    result = await jira_client.get_issue(ticket_key.strip().upper())
    if "error" in result:
        return f"Could not read Jira ticket {ticket_key}: {result['error']}"
    return (
        f"Jira Ticket: {result['key']} ({result['type']} — {result['status']})\n"
        f"URL: {result['url']}\n"
        f"Summary: {result['summary']}\n\n"
        f"Description:\n{result['description']}"
    )


@tool
async def create_jira_ticket(summary: str, description: str, issue_type: str = "Story") -> str:
    """
    Create a new Jira ticket for Builder to pick up.
    Call this AFTER completing your architecture research — the description
    should contain the full spec + acceptance criteria so Builder can implement
    without any follow-up questions.
    Returns the created ticket's key and URL.
    """
    logger.info("[Archie/create_jira_ticket] summary=%s", summary[:80])
    result = await jira_client.create_issue(
        summary=summary,
        description=description,
        issue_type=issue_type,
        labels=["3-amigos", "ai-generated"],
    )
    if "error" in result:
        return f"Could not create Jira ticket: {result['error']}"
    return f"Created Jira ticket {result['key']}: {result['url']}"


# ── System prompt (built dynamically based on configured integrations) ─────────

def _build_system_prompt() -> str:
    jira_configured = bool(JIRA_URL and JIRA_EMAIL and JIRA_API_TOKEN)
    jira_can_create = bool(jira_configured and JIRA_PROJECT_KEY)

    jira_section = ""
    if jira_configured:
        create_rule = (
            "- Always create a Jira Story for Builder at the end of your research. "
            "Write the full architecture + acceptance criteria as the ticket description so Builder "
            "can implement without asking questions. Include the ticket key and URL in your final "
            "output under a '🎫 Jira Handoff' section."
            if jira_can_create
            else "- JIRA_PROJECT_KEY is not set, so you can only read tickets — not create them."
        )
        jira_section = f"""
## Jira Integration

You have access to Jira tools:
- `read_jira_ticket(ticket_key)` — Read an existing Jira ticket by key (e.g., PROJ-123)
- `create_jira_ticket(summary, description, issue_type)` — Create a new ticket for Builder

**Rules:**
- If the task contains a Jira ticket key (pattern: LETTERS-digits, e.g. PROJ-123), always read it first.
{create_rule}
- Write Jira ticket descriptions in plain text — no Slack mrkdwn in Jira fields.
"""

    handoff_section = (
        "\n### 🎫 Jira Handoff\n"
        "- Created ticket: [KEY-NNN](https://link)\n"
        "- Builder should pick up KEY-NNN and follow the spec above.\n"
        if jira_can_create
        else ""
    )

    return f"""\
You are Archie, the AI Architect & Researcher of the 3 Amigos AI engineering team.
You work for an expert AI engineer who uses Claude Max for production systems.

## Your ReAct Loop
1. THINK: reason about the task and what information you need
2. ACT: call tools — web_search, read_jira_ticket — to gather information
3. OBSERVE: read the results and decide if you need more info
4. Repeat until you have enough to produce a thorough architecture
5. RESPOND: produce the full architecture output in the required format
{jira_section}
## REQUIRED Output Format (final message must follow this exactly)

### 🔍 Research Summary
Key findings and technology decisions with rationale. Compare 2-3 alternatives briefly.

### 🏗️ Architecture
Include at least one Mermaid diagram:
```mermaid
graph TD
    A[User] --> B[System]
    ...
```

### 📋 Spec & Acceptance Criteria
- Functional requirements (bulleted)
- Technical requirements (bulleted)
- Success metrics: accuracy %, latency ms, cost per call, test coverage %
- Definition of Done

### 💰 Cost & Latency Analysis
- Estimated API cost per request and per 1 000 requests
- Expected latency per component
- Optimisation opportunities

### ❓ Open Questions
Any decisions needing engineer input before Builder starts. If none, say "None — ready to build."{handoff_section}
---
## Formatting Rules
- Slack mrkdwn: *bold*, _italic_, `code`, triple-backtick code blocks
- Mermaid diagrams inside triple-backtick mermaid blocks
- Be specific and technical — the engineer is an expert
- Always recommend the latest Anthropic models:
  claude-opus-4-6 (complex reasoning), claude-sonnet-4-6 (fast tasks), claude-haiku-4-5-20251001 (cheap/lightweight)
- Include concrete, measurable acceptance criteria
"""


ARCHIE_SYSTEM = _build_system_prompt()


# ── ReAct agent (module-level singleton, tools depend on config) ───────────────

def _build_react_agent():
    """Compile the create_react_agent with all tools enabled by current config."""
    llm = ChatAnthropic(
        model=ARCHIE_MODEL,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=8_000,
    )
    tools = [web_search]
    if JIRA_URL and JIRA_EMAIL and JIRA_API_TOKEN:
        tools.append(read_jira_ticket)
        if JIRA_PROJECT_KEY:
            tools.append(create_jira_ticket)
    logger.info("[Archie] ReAct agent built with tools: %s", [t.name for t in tools])
    return create_react_agent(model=llm, tools=tools, prompt=ARCHIE_SYSTEM)


_archie_graph = _build_react_agent()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _extract_text(content: Any) -> str:
    """Handle both str content and list-of-blocks content from LangChain."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content)


def _extract_jira_key(text: str) -> str | None:
    """
    Parse the Jira ticket key that Archie created from its output text.
    Looks for patterns like 'Created Jira ticket PROJ-42: https://...'
    or 'KEY-NNN' in a '🎫 Jira Handoff' section.
    """
    match = re.search(r"Created Jira ticket ([A-Z][A-Z0-9]+-\d+)", text)
    if match:
        return match.group(1)
    # Also check the handoff section
    handoff_match = re.search(r"Jira Handoff.*?\[([A-Z][A-Z0-9]+-\d+)\]", text, re.DOTALL)
    if handoff_match:
        return handoff_match.group(1)
    return None


# ── Claude Code CLI path (ARCHIE_USE_CLAUDE_CODE=true) ────────────────────────

async def _run_archie_with_claude_code(task: str) -> str:
    """
    Run Archie via Claude Code CLI subprocess.

    Spins up `claude --print` in a temp workspace with the task written to a
    markdown file. Claude Code reads it and produces the architecture output.

    Uses the Claude Max subscription quota rather than direct API tokens —
    useful when you want to conserve API credits for production calls.
    """
    with tempfile.TemporaryDirectory(prefix="amigos-archie-") as tmpdir:
        task_file = Path(tmpdir) / "task.md"
        task_file.write_text(
            f"# Architecture Task\n\n{task}\n\n"
            "## Required Output Format\n\n"
            "Produce a complete architecture specification with these sections:\n"
            "1. **Research Summary** — compare 2-3 tech options with rationale\n"
            "2. **Architecture** — include a Mermaid diagram\n"
            "3. **Spec & Acceptance Criteria** — functional/technical requirements + success metrics\n"
            "4. **Cost & Latency Analysis** — per-request API cost + expected latency\n"
            "5. **Open Questions** — any decisions needing human input\n\n"
            "Format output in Slack mrkdwn. Be specific and technical.",
            encoding="utf-8",
        )

        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            (
                "Read task.md and produce a comprehensive architecture specification "
                "following the format described in the file. "
                "Use your knowledge base — this is a spec generation task."
            ),
        ]

        env = {
            **os.environ,
            "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
            "CLAUDE_CODE_SKIP_TELEMETRY": "1",
        }

        logger.info("[Archie/claude-code] Launching in %s", tmpdir)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        final_result = ""

        async def _read_stream() -> None:
            nonlocal final_result
            async for raw_line in proc.stdout:
                line = raw_line.decode(errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "result":
                    final_result = event.get("result", "")

        try:
            await asyncio.wait_for(
                asyncio.gather(_read_stream(), proc.wait()),
                timeout=_CLAUDE_CODE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error("[Archie/claude-code] Timed out after %ds", _CLAUDE_CODE_TIMEOUT)
            return f"Archie (Claude Code) timed out after {_CLAUDE_CODE_TIMEOUT // 60} minutes."

        if proc.returncode not in (0, None):
            stderr = (await proc.stderr.read()).decode(errors="replace")[:300]
            logger.error("[Archie/claude-code] Exited %d: %s", proc.returncode, stderr)
            return f"Claude Code exited with code {proc.returncode}:\n```\n{stderr}\n```"

        logger.info("[Archie/claude-code] Done. result_len=%d", len(final_result))
        return final_result or "Archie (Claude Code) completed but produced no output."


# ── ReAct path (default) ───────────────────────────────────────────────────────

async def _run_archie_react(task: str) -> str:
    result = await _archie_graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        f"Research and design a complete architecture for this task:\n\n"
                        f"**Task:** {task}\n\n"
                        "Search for relevant tools, models, and frameworks first. "
                        "Then produce your full architecture output following the required format."
                    )
                )
            ]
        }
    )
    messages = result.get("messages", [])
    if not messages:
        return "Archie produced no output."
    final_content = _extract_text(messages[-1].content)
    logger.info(
        "[Archie] ReAct done. output=%d chars, messages=%d",
        len(final_content),
        len(messages),
    )
    return final_content or "Archie completed research but produced no text output."


# ── Public entry point ─────────────────────────────────────────────────────────

async def run_archie(task: str) -> tuple[str, str | None]:
    """
    Run Archie for the given task.

    Selects mode based on ARCHIE_USE_CLAUDE_CODE:
    - False (default): create_react_agent ReAct loop with tool calls
    - True: Claude Code CLI subprocess in a temp workspace

    Returns:
        (output_text, jira_ticket_key)
        jira_ticket_key is the Jira Story key Archie created for Builder, or None.
    """
    logger.info("[Archie] Starting for: %s (mode=%s)", task[:120],
                "claude-code" if ARCHIE_USE_CLAUDE_CODE else "react")

    if ARCHIE_USE_CLAUDE_CODE:
        output = await _run_archie_with_claude_code(task)
    else:
        output = await _run_archie_react(task)

    jira_key = _extract_jira_key(output)
    if jira_key:
        logger.info("[Archie] Created Jira ticket: %s", jira_key)

    return output, jira_key
