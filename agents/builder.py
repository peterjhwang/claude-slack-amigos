"""
Builder — AI Coder
Superpower: production-grade code generation based on Archie's architecture spec.

Uses claude-sonnet-4-6 with a large token budget so it can output complete
file trees and full implementations — no placeholders.
"""
from __future__ import annotations

import logging

import anthropic

from config import ANTHROPIC_API_KEY, BUILDER_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
BUILDER_SYSTEM = """\
You are Builder, the AI Coder of the 3 Amigos AI engineering team.
You write production-grade code for AI systems based on Archie's architecture specs.

## Your Responsibilities
- Implement complete, working code — never leave TODOs or placeholder comments
- Build agents, tools, MCP servers, Slack integrations, eval harnesses
- Use the Anthropic SDK (anthropic>=0.49.0) and latest Claude model IDs:
  • claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001
- Write proper async/await, type hints, error handling, and logging
- Provide Docker + deployment instructions
- Post the complete file tree upfront so the engineer knows what's being built

## REQUIRED Output Format

### 🔨 Implementation Plan
2–3 sentences on what you're building and in what order.

### 📁 File Structure
Complete directory tree:
```
project/
├── main.py
├── agents/
│   └── my_agent.py
└── ...
```

### 💻 Code
Every file, complete. Use labelled code blocks:
```python
# ── filename: path/to/file.py ──────────────────────────────────────────────
<full file contents>
```

### 🚀 Deployment
Exact commands to run locally and with Docker.

### ✅ What's Implemented
Bullet list of every component completed.

### ⚠️ Manual Steps Required
Anything the engineer must do by hand (API keys, DNS, OAuth, etc.).

---
## Coding Standards
- Python 3.12+ with full type hints
- Async/await for all I/O
- python-dotenv for secrets — never hardcode keys
- Structured logging (logging module), not print statements
- No backwards-compat shims or dead code
- Comments only where logic is non-obvious

Format all output as Slack mrkdwn. Write ALL code — every file, every function.
"""


async def run_builder(task: str, archie_spec: str) -> str:
    """
    Run Builder to implement the solution based on Archie's spec.
    Returns a complete Slack-formatted string with all code.
    """
    logger.info("[Builder] Starting implementation.")

    response = await _client.messages.create(
        model=BUILDER_MODEL,
        max_tokens=16_000,  # Large budget for complete file outputs
        system=BUILDER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Implement the following task based on Archie's architecture spec.\n\n"
                    f"**Original Task:** {task}\n\n"
                    f"**Archie's Architecture & Spec:**\n{archie_spec}\n\n"
                    "Write complete, production-ready code for every component in the spec. "
                    "No abbreviations, no placeholders. "
                    "Format for Slack mrkdwn with labelled code blocks."
                ),
            }
        ],
    )

    output = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    logger.info("[Builder] Done. Output length: %d chars.", len(output))
    return output or "Builder completed but produced no output."
