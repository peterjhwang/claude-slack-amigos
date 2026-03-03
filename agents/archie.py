"""
Archie — AI Architect & Researcher
Framework: LangGraph `create_react_agent` (prebuilt ReAct loop)
Model: claude-opus-4-6

Archie runs a full ReAct (Reason + Act) loop internally:
  Think → search the web → think → search again → … → draft architecture

`create_react_agent` wires up:
  - A LangChain ChatAnthropic model (tool-calling capable)
  - A list of LangChain tools (web_search)
  - A system prompt that enforces the output format
  - The standard message-passing state (MessagesState)

The agent loops autonomously until Claude decides it has enough
information to produce the final architecture output, then stops.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from config import ANTHROPIC_API_KEY, ARCHIE_MODEL
from tools.search import web_search as _do_web_search

logger = logging.getLogger(__name__)

# ── LangChain tool (wraps the existing Tavily helper) ─────────────────────────
@tool
async def web_search(query: str) -> str:
    """
    Search the web for current information about AI models, tools, frameworks,
    APIs, benchmarks, and pricing. Use this to verify up-to-date choices before
    committing to an architecture recommendation.
    """
    logger.info("[Archie/web_search] query=%s", query[:120])
    return await _do_web_search(query)


# ── System prompt ─────────────────────────────────────────────────────────────
ARCHIE_SYSTEM = """\
You are Archie, the AI Architect & Researcher of the 3 Amigos AI engineering team.
You work for an expert AI engineer who uses Claude Max for production systems.

## Your ReAct Loop
1. THINK: reason about the task and what information you need
2. ACT: call web_search to verify up-to-date facts (models, pricing, APIs, benchmarks)
3. OBSERVE: read the results and decide if you need more info
4. Repeat until you have enough to produce a thorough architecture
5. RESPOND: produce the full architecture output in the required format

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
Any decisions needing engineer input before Builder starts. If none, say "None — ready to build."

---
## Formatting Rules
- Slack mrkdwn: *bold*, _italic_, `code`, triple-backtick code blocks
- Mermaid diagrams inside triple-backtick mermaid blocks
- Be specific and technical — the engineer is an expert
- Always recommend the latest Anthropic models:
  claude-opus-4-6 (complex reasoning), claude-sonnet-4-6 (fast tasks), claude-haiku-4-5-20251001 (cheap/lightweight)
- Include concrete, measurable acceptance criteria
"""

# ── Build the ReAct agent (module-level singleton) ────────────────────────────
_llm = ChatAnthropic(
    model=ARCHIE_MODEL,
    api_key=ANTHROPIC_API_KEY,
    max_tokens=8_000,
)

# create_react_agent builds the full ReAct graph:
#   START → agent_node ← [tool_node loops back] → END
# The agent calls tools until it decides to stop, then produces the final answer.
_archie_graph = create_react_agent(
    model=_llm,
    tools=[web_search],
    prompt=ARCHIE_SYSTEM,   # system message injected at the start of every run
)


# ── Helper: extract text from the last LangChain message ─────────────────────
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


# ── Public entry point ────────────────────────────────────────────────────────
async def run_archie(task: str) -> str:
    """
    Run Archie's ReAct loop for the given task.
    The agent researches autonomously (web searches) then produces
    a complete architecture + spec formatted for Slack.

    Returns a Slack mrkdwn string ready to post.
    """
    logger.info("[Archie] Starting ReAct loop for: %s", task[:120])

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

    # The last message in the thread is Archie's final response
    messages = result.get("messages", [])
    if not messages:
        return "Archie produced no output."

    final_content = _extract_text(messages[-1].content)
    logger.info("[Archie] Done. Output: %d chars, %d messages exchanged.", len(final_content), len(messages))
    return final_content or "Archie completed research but produced no text output."
