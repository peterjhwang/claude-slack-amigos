"""
Archie — AI Architect & Researcher
Superpower: deep research + system design.

Uses claude-opus-4-6 with an agentic tool-use loop so it can web-search
before committing to an architecture. Falls back gracefully if Tavily
is not configured.
"""
from __future__ import annotations

import logging

import anthropic

from config import ANTHROPIC_API_KEY, ARCHIE_MODEL
from tools.search import web_search

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
ARCHIE_SYSTEM = """\
You are Archie, the AI Architect & Researcher of the 3 Amigos AI engineering team.
You work for an expert AI engineer who uses Claude Max for production systems.

## Your Responsibilities
- Research and select optimal models, tools, and frameworks
  (Claude API, embeddings, vector DBs, LangGraph, CrewAI, MCP servers, Tavily, etc.)
- Design complete system architectures with Mermaid diagrams
- Create prompt strategies and agent graph designs
- Perform cost/latency analysis
- Write detailed technical specs with clear acceptance criteria and AI metrics
- Ask for engineer sign-off before handing off to Builder

## REQUIRED Output Format (always use exactly this structure)

### 🔍 Research Summary
Key findings and technology decisions with rationale. Compare alternatives briefly.

### 🏗️ Architecture
Include at least one Mermaid diagram:
```mermaid
graph TD
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
- Use Slack mrkdwn: *bold*, _italic_, `code`, ```code blocks```
- Mermaid diagrams go inside triple-backtick mermaid blocks
- Be specific and technical — the engineer is an expert
- Always recommend the latest Anthropic models:
  • claude-opus-4-6 for complex reasoning tasks
  • claude-sonnet-4-6 for fast, high-volume tasks
  • claude-haiku-4-5-20251001 for lightweight / cheap tasks
- Always include concrete, measurable acceptance criteria
"""

# ── Tool definitions for Anthropic API tool_use ───────────────────────────────
_TOOLS: list[dict] = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information about AI models, frameworks, APIs, "
            "pricing, benchmarks, and engineering best practices. "
            "Use this to verify up-to-date info before recommending a stack."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Specific search query, e.g. "
                        "'LangGraph vs CrewAI 2025 async performance' or "
                        "'claude-opus-4-6 pricing per million tokens'"
                    ),
                }
            },
            "required": ["query"],
        },
    }
]


# ── Main agent function ───────────────────────────────────────────────────────
async def run_archie(task: str) -> str:
    """
    Run Archie's research-and-design loop for the given task.
    Returns a fully formatted Slack mrkdwn string ready to post.
    """
    logger.info("[Archie] Starting research for: %s", task[:120])

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Research and design a complete architecture for this task:\n\n"
                f"**Task:** {task}\n\n"
                "Search the web for relevant tools, models, and frameworks. "
                "Then produce your full architecture output following the required format."
            ),
        }
    ]

    # Agentic tool-use loop (max 6 iterations to control cost)
    for iteration in range(6):
        response = await _client.messages.create(
            model=ARCHIE_MODEL,
            max_tokens=8_000,
            system=ARCHIE_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )

        text_parts: list[str] = []
        tool_uses: list = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if response.stop_reason == "end_turn":
            result = "".join(text_parts).strip()
            logger.info("[Archie] Done after %d iteration(s).", iteration + 1)
            return result or "Archie completed research but produced no text output."

        if response.stop_reason == "tool_use" and tool_uses:
            # Execute each tool call
            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict] = []
            for tu in tool_uses:
                if tu.name == "web_search":
                    logger.info("[Archie] Searching: %s", tu.input.get("query", ""))
                    result = await web_search(tu.input["query"])
                else:
                    result = f"Unknown tool: {tu.name}"
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id, "content": result}
                )
            messages.append({"role": "user", "content": tool_results})
        else:
            # stop_reason is something unexpected — return what we have
            return "".join(text_parts).strip() or "Archie stopped unexpectedly."

    return (
        "Archie hit the research iteration limit. "
        "Try a more specific task or increase max iterations."
    )
