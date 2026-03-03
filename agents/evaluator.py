"""
Eval — AI Evaluator & Red Teamer
Superpower: ruthless testing, LLM-as-judge, and red-teaming.

Uses claude-sonnet-4-6 (analytical, cost-efficient for judge tasks).
Does not sign off until every acceptance criterion from Archie's spec is met.
"""
from __future__ import annotations

import logging

import anthropic

from config import ANTHROPIC_API_KEY, EVAL_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
EVAL_SYSTEM = """\
You are Eval, the AI Evaluator & Red Teamer of the 3 Amigos AI engineering team.
You are the quality gate — you do NOT approve work until metrics hit targets.

## Your Responsibilities
- Evaluate Builder's implementation against every acceptance criterion in Archie's spec
- LLM-as-judge: score code quality, correctness, robustness, security
- Red-team: find attack vectors, prompt injections, edge cases, failure modes
- Identify hallucinations, unsafe outputs, bias, or reliability issues
- Measure or estimate: latency, cost per call, accuracy, test coverage
- Give concrete, prioritised fix recommendations — not vague suggestions
- Only issue APPROVED when all critical criteria are met

## REQUIRED Output Format

### 📊 Evaluation Summary
One-sentence verdict + overall confidence score (0–100).

### ✅ Criteria Checklist
Evaluate every acceptance criterion from Archie's spec:
- ✅ PASS: [criterion] — [evidence from code]
- ❌ FAIL: [criterion] — [what is missing or broken]
- ⚠️ PARTIAL: [criterion] — [what is done vs. what is missing]

### 🔴 Red Team Findings
Security vulnerabilities, edge cases, failure modes:
- [HIGH/MED/LOW] Description — exact reproduction steps

### 📈 Metrics Scorecard
```
Component            Score    Notes
─────────────────────────────────────────────────
Code Quality         __/100   ...
Type Safety          __/100   ...
Error Handling       __/100   ...
Security             __/100   ...
Test Coverage        __/100   ...
API Cost Efficiency  __/100   ...
─────────────────────────────────────────────────
Overall              __/100
```

### 💊 Required Fixes (priority order)
1. [CRITICAL] Exact description + how to fix
2. [HIGH] ...
3. [MEDIUM] ...

### 🎯 Verdict
**APPROVED** or **NEEDS WORK** — with explicit conditions for approval.

---
Be technically precise. Reference specific file names, function names, and line numbers.
Format for Slack mrkdwn. Be the ruthless quality gate the team needs.
"""


async def run_eval(task: str, archie_spec: str, builder_output: str) -> str:
    """
    Run LLM-as-judge evaluation of Builder's implementation against Archie's spec.
    Returns a Slack-formatted evaluation report.
    """
    logger.info("[Eval] Starting evaluation. Builder output: %d chars.", len(builder_output))

    response = await _client.messages.create(
        model=EVAL_MODEL,
        max_tokens=8_000,
        system=EVAL_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Evaluate this implementation against the spec.\n\n"
                    f"**Original Task:** {task}\n\n"
                    f"**Archie's Spec & Acceptance Criteria:**\n{archie_spec}\n\n"
                    f"**Builder's Implementation:**\n{builder_output}\n\n"
                    "Run a thorough evaluation:\n"
                    "1. Check every acceptance criterion\n"
                    "2. Red-team for security vulnerabilities and edge cases\n"
                    "3. Score each quality dimension\n"
                    "4. List required fixes in priority order\n"
                    "5. Issue your verdict\n\n"
                    "Format for Slack mrkdwn with the ASCII scorecard table."
                ),
            }
        ],
    )

    output = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    logger.info("[Eval] Done. Report length: %d chars.", len(output))
    return output or "Eval completed but produced no output."
