"""
Eval — AI Evaluator & Red Teamer
Framework: Custom LangGraph StateGraph (4-node sequential pipeline)
Model: claude-sonnet-4-6

Each node is a focused, specialist LLM call. The pipeline is:

  parse_criteria ──► assess_code ──► red_team ──► score_and_verdict ──► END
        │                 │               │                │
   Extracts &        Checks each      Attacks the      Produces ASCII
   structures        criterion        implementation    scorecard +
   acceptance        (PASS/FAIL/       for security     final verdict
   criteria          PARTIAL)         & edge cases

This is deliberately a pipeline (no branching), not a loop —
Eval runs each phase exactly once and synthesises at the end.
Using a StateGraph gives us:
  - Explicit, inspectable state at every node boundary
  - Easy to add/reorder nodes as evaluation needs grow
  - Consistent with the outer 3-Amigos LangGraph pattern
"""
from __future__ import annotations

import logging
from typing import Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from config import EVALUATOR_PERSONA
from tools.llm import make_llm

logger = logging.getLogger(__name__)

_llm = make_llm(EVALUATOR_PERSONA["model"])


# ── Pipeline state ─────────────────────────────────────────────────────────────
class EvalState(TypedDict):
    # Inputs (set once at invocation)
    task: str
    researcher_spec: str
    builder_output: str

    # Outputs — each node fills its own field
    parsed_criteria: Optional[str]    # node 1: structured acceptance criteria
    code_assessment: Optional[str]    # node 2: per-criterion pass/fail analysis
    red_team_report: Optional[str]    # node 3: security & edge-case findings
    scorecard: Optional[str]          # node 4: ASCII metrics table + verdict


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _extract_text(content) -> str:
    """Normalise LangChain response content to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content)


async def _call(system: str, user: str, max_tokens: int = 4_000) -> str:
    llm = _llm.bind(max_tokens=max_tokens)
    result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
    return _extract_text(result.content).strip()


# ── Node 1: Parse & structure acceptance criteria ──────────────────────────────
async def parse_criteria_node(state: EvalState) -> dict:
    """
    Read Archie's spec and extract a clean, numbered list of acceptance criteria.
    This gives the next node a precise checklist to evaluate against — rather than
    asking a single model to do both extraction and evaluation in one pass.
    """
    logger.info("[Eval/parse_criteria] Extracting acceptance criteria")

    system = """\
You are a precise requirements analyst. Extract and structure acceptance criteria from an architecture spec.

Output format — a numbered list, each item on its own line:
1. [FUNCTIONAL] Description of the criterion
2. [TECHNICAL] Description
3. [METRIC] Specific measurable target (e.g. "p99 latency < 500ms", "test coverage >= 80%")
...

Be exhaustive. If the spec is vague, infer reasonable criteria for a production AI system.
Include implicit requirements (error handling, logging, type hints, async, etc.).
"""
    text = await _call(
        system,
        f"Task: {state['task']}\n\nArchie's Spec:\n{state['researcher_spec']}"
    )
    logger.info("[Eval/parse_criteria] Extracted %d chars of criteria", len(text))
    return {"parsed_criteria": text}


# ── Node 2: Assess implementation against each criterion ──────────────────────
async def assess_code_node(state: EvalState) -> dict:
    """
    Go through each acceptance criterion and mark it PASS / FAIL / PARTIAL.
    References specific file names and function names from Builder's output.
    """
    logger.info("[Eval/assess_code] Evaluating implementation against criteria")

    system = """\
You are an expert code reviewer doing LLM-as-judge evaluation.
You are given: (a) a numbered list of acceptance criteria, (b) a code implementation.

For every criterion, output exactly one line:
  ✅ PASS  [#N] criterion text — evidence from the code
  ❌ FAIL  [#N] criterion text — what is missing or wrong
  ⚠️ PARTIAL [#N] criterion text — what is done vs. what is missing

Reference specific file names, function names, and line snippets where possible.
Be strict — "looks like it might work" is not a PASS.
"""
    text = await _call(
        system,
        (
            f"Acceptance Criteria:\n{state['parsed_criteria']}\n\n"
            f"Implementation:\n{state['builder_output']}"
        ),
        max_tokens=5_000,
    )
    logger.info("[Eval/assess_code] Assessment: %d chars", len(text))
    return {"code_assessment": text}


# ── Node 3: Red-team the implementation ───────────────────────────────────────
async def red_team_node(state: EvalState) -> dict:
    """
    Actively attack the implementation — security vulnerabilities, prompt injection,
    edge cases, failure modes, bias, and reliability issues.
    """
    logger.info("[Eval/red_team] Running red-team analysis")

    system = """\
You are an adversarial security researcher and reliability engineer.
Your job is to break the implementation — find every flaw before it ships.

Check for:
- Security: secrets in code, injection attacks, unvalidated inputs, insecure defaults
- Prompt injection: if this is an AI system, can the input manipulate the model?
- Edge cases: empty inputs, very long inputs, unicode, concurrent requests, timeouts
- Failure modes: what happens when an API is down? Rate-limited? Returns unexpected data?
- Resource leaks: unclosed connections, unbounded memory, missing cleanup
- Bias / safety: any harmful outputs possible?

Format each finding as:
[HIGH/MED/LOW] Title
  → Attack/reproduction: <exact steps>
  → Impact: <what breaks>
  → Fix: <specific remediation>

If the implementation is genuinely solid in an area, say so briefly. Don't invent issues.
"""
    text = await _call(
        system,
        (
            f"Task: {state['task']}\n\n"
            f"Implementation to attack:\n{state['builder_output']}"
        ),
        max_tokens=4_000,
    )
    logger.info("[Eval/red_team] Red-team report: %d chars", len(text))
    return {"red_team_report": text}


# ── Node 4: Score and produce final verdict ────────────────────────────────────
async def score_and_verdict_node(state: EvalState) -> dict:
    """
    Synthesise the previous three nodes into:
    - An ASCII metrics scorecard
    - Required fixes in priority order
    - A final APPROVED / NEEDS WORK verdict
    """
    logger.info("[Eval/score_and_verdict] Producing scorecard and verdict")

    system = """\
You are the final quality gate for an AI engineering team.
You receive: criteria assessment, red-team findings.
Produce a structured evaluation report for the engineer.

Required sections (in this order):

### 📊 Evaluation Summary
One sentence verdict + overall confidence score (0-100).

### ✅ Criteria Checklist
Paste the criteria assessment as-is (already computed).

### 🔴 Red Team Findings
Paste the red-team report as-is (already computed).

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
1. [CRITICAL] …
2. [HIGH] …
3. [MEDIUM] …

### 🎯 Verdict
**APPROVED** or **NEEDS WORK** — with explicit conditions for approval.

Format for Slack mrkdwn.
"""
    text = await _call(
        system,
        (
            f"Task: {state['task']}\n\n"
            f"Criteria Assessment:\n{state['code_assessment']}\n\n"
            f"Red-Team Report:\n{state['red_team_report']}"
        ),
        max_tokens=5_000,
    )
    logger.info("[Eval/score_and_verdict] Final report: %d chars", len(text))
    return {"scorecard": text}


# ── Build the pipeline graph (module-level singleton) ─────────────────────────
def _build_eval_graph():
    builder = StateGraph(EvalState)

    builder.add_node("parse_criteria",    parse_criteria_node)
    builder.add_node("assess_code",       assess_code_node)
    builder.add_node("red_team",          red_team_node)
    builder.add_node("score_and_verdict", score_and_verdict_node)

    builder.set_entry_point("parse_criteria")
    builder.add_edge("parse_criteria",    "assess_code")
    builder.add_edge("assess_code",       "red_team")
    builder.add_edge("red_team",          "score_and_verdict")
    builder.add_edge("score_and_verdict", END)

    return builder.compile()


_eval_graph = _build_eval_graph()


# ── Public entry point ────────────────────────────────────────────────────────
async def run_eval(task: str, researcher_spec: str, builder_output: str) -> str:
    """
    Run the 4-node Eval pipeline:
      parse_criteria → assess_code → red_team → score_and_verdict

    Each node is a focused LLM call; the StateGraph passes outputs
    downstream via EvalState. Returns the final Slack-formatted report.
    """
    logger.info("[Eval] Starting 4-node pipeline")

    result = await _eval_graph.ainvoke(
        EvalState(
            task=task,
            researcher_spec=researcher_spec,
            builder_output=builder_output,
            parsed_criteria=None,
            code_assessment=None,
            red_team_report=None,
            scorecard=None,
        )
    )

    final_report = result.get("scorecard", "")
    logger.info("[Eval] Pipeline complete. Report: %d chars", len(final_report))
    return final_report or "Eval pipeline completed but produced no output."
