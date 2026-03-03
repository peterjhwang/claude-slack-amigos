"""
Builder — AI Coder (powered by Claude Code CLI)
================================================
Instead of running an in-process agentic loop, Builder delegates all coding
to the Claude Code CLI (`claude --print`), which is the same engine that
powers the IDE plugin and VS Code extension.

Flow per task
-------------
1. Clone GITHUB_REPO (or `git init` if no repo configured)
2. Create a feature branch:  feature/amigos-<build_id[:12]>
3. Write Archie's spec to `.amigos_task.md` in the repo root
4. Run:  claude --print --dangerously-skip-permissions \
                  --output-format stream-json  "<prompt>"
   Claude Code streams NDJSON events; we parse them for real-time Slack updates.
5. After Claude Code exits: git add -A && git commit
6. Push + open PR with `gh pr create` -> capture the PR URL
7. Post PR link to Slack

Fallback (no GITHUB_TOKEN / GITHUB_REPO)
-----------------------------------------
Builder runs in a local sandbox (/tmp/amigos-builds/<build_id>/),
skips push/PR, and returns the summary text only.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from config import (
    ANTHROPIC_API_KEY,
    GITHUB_BASE_BRANCH,
    GITHUB_REPO,
    GITHUB_TOKEN,
)

logger = logging.getLogger(__name__)

_BUILD_ROOT = Path(os.getenv("BUILD_ROOT", "/tmp/amigos-builds"))

# How long to wait for Claude Code to finish (10 min — complex tasks can be slow)
_CLAUDE_CODE_TIMEOUT = 600


# -- Git / GitHub helpers ------------------------------------------------------

async def _bash(cwd: Path, command: str, env: dict | None = None) -> tuple[int, str]:
    """Run a shell command; return (returncode, stdout+stderr)."""
    merged_env = {**os.environ, **(env or {})}
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=merged_env,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    return proc.returncode, stdout.decode(errors="replace").strip()


async def _setup_workspace(build_id: str) -> tuple[Path, str]:
    """
    Clone GITHUB_REPO into a fresh sandbox, or `git init` a local dir.
    Returns (build_dir, branch_name).
    """
    build_dir = _BUILD_ROOT / build_id
    build_dir.mkdir(parents=True, exist_ok=True)
    branch = f"feature/amigos-{build_id[:12]}"

    if GITHUB_TOKEN and GITHUB_REPO:
        # Authenticated clone -- embed token in URL so push works without prompts
        clone_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        rc, out = await _bash(
            _BUILD_ROOT,
            f"git clone --depth 1 --branch {GITHUB_BASE_BRANCH} {clone_url} {build_id}",
        )
        if rc != 0:
            logger.warning("[Builder] Clone failed (%s), falling back to git init", out[:200])
            await _bash(build_dir, "git init")
    else:
        # No GitHub config -- local-only sandbox
        await _bash(build_dir, "git init")

    # Create the feature branch
    await _bash(build_dir, f"git checkout -b {branch}")
    logger.info("[Builder] Workspace ready: %s (branch: %s)", build_dir, branch)
    return build_dir, branch


async def _create_pr(build_dir: Path, branch: str, task: str) -> str | None:
    """
    Push the branch and open a GitHub PR.
    Returns the PR URL, or None if push/PR fails.
    """
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None

    gh_env = {"GH_TOKEN": GITHUB_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN}

    # Commit anything Claude Code didn't commit itself
    await _bash(
        build_dir,
        'git add -A && git diff --cached --quiet || git commit -m "feat: 3 Amigos build"',
        gh_env,
    )

    # Push
    rc, out = await _bash(build_dir, f"git push -u origin {branch}", gh_env)
    if rc != 0:
        logger.warning("[Builder] Push failed: %s", out[:300])
        return None

    # Create PR with gh CLI
    pr_title = task[:72].replace('"', "'")
    pr_body = (
        "## Built by 3 Amigos\\n\\n"
        f"**Task:** {task}\\n\\n"
        "This PR was generated autonomously by the 3 Amigos AI team:\\n"
        "- Archie designed the architecture\\n"
        "- Builder implemented it with Claude Code\\n"
        "- Eval will review it next\\n\\n"
        "_Generated with Claude Code via the 3 Amigos Slack bot_"
    )
    rc, out = await _bash(
        build_dir,
        f'gh pr create --title "{pr_title}" --body "{pr_body}" '
        f"--base {GITHUB_BASE_BRANCH} --head {branch}",
        gh_env,
    )
    if rc != 0:
        logger.warning("[Builder] gh pr create failed: %s", out[:300])
        return None

    # gh pr create prints the PR URL as the last line
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("https://github.com/"):
            logger.info("[Builder] PR created: %s", line)
            return line

    return None


# -- Claude Code CLI runner ----------------------------------------------------

async def _run_claude_code(
    build_dir: Path,
    prompt: str,
    progress_callback: Callable[[str], Awaitable[None]] | None,
) -> str:
    """
    Invoke `claude --print` in stream-json mode.

    Claude Code streams NDJSON events:
      {"type": "assistant", "message": {"content": [{"type": "text", ...}]}}
      {"type": "tool_result", ...}
      {"type": "result", "subtype": "success", "result": "...", "num_turns": N}

    We parse these to post real-time progress to Slack and capture the final result.
    """
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",   # no interactive prompts in automation
        "--output-format", "stream-json",
        prompt,
    ]

    env = {
        **os.environ,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "CLAUDE_CODE_SKIP_TELEMETRY": "1",
    }

    logger.info("[Builder] Launching Claude Code CLI in %s", build_dir)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(build_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    tool_count = 0
    last_progress_at = 0
    final_result = ""
    current_activity = "initialising"

    async def _read_stream() -> None:
        nonlocal tool_count, last_progress_at, final_result, current_activity

        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type", "")

            if etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        snippet = block["text"][:80].replace("\n", " ")
                        if snippet:
                            current_activity = snippet

            elif etype == "tool_result":
                tool_count += 1
                if progress_callback and (tool_count - last_progress_at) >= 4:
                    last_progress_at = tool_count
                    await progress_callback(
                        f"🔨 *Claude Code — {tool_count} operations*\n"
                        f"_{current_activity}_"
                    )

            elif etype == "result":
                final_result = event.get("result", "")
                num_turns = event.get("num_turns", tool_count)
                logger.info(
                    "[Builder] Claude Code done. turns=%d result_len=%d",
                    num_turns, len(final_result),
                )

    try:
        await asyncio.wait_for(
            asyncio.gather(_read_stream(), proc.wait()),
            timeout=_CLAUDE_CODE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        proc.kill()
        logger.error("[Builder] Claude Code timed out after %ds", _CLAUDE_CODE_TIMEOUT)
        return f"Claude Code timed out after {_CLAUDE_CODE_TIMEOUT // 60} minutes."

    if proc.returncode not in (0, None):
        stderr = (await proc.stderr.read()).decode(errors="replace")[:500]
        logger.error("[Builder] Claude Code exited %d: %s", proc.returncode, stderr)
        return f"Claude Code exited with code {proc.returncode}.\n```\n{stderr}\n```"

    return final_result or "Claude Code completed (no result text captured)."


# -- Public entry point --------------------------------------------------------

async def run_builder(
    task: str,
    archie_spec: str,
    build_id: str = "default",
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[str, str | None]:
    """
    Run Builder end-to-end:
      clone/init → spec file → Claude Code CLI → commit → push → PR → summary

    Returns:
      (summary_text, pr_url)
      pr_url is None when GITHUB_TOKEN / GITHUB_REPO are not configured.
    """
    build_dir, branch = await _setup_workspace(build_id)

    # Write the full spec to disk so Claude Code reads it with its file tools
    spec_file = build_dir / ".amigos_task.md"
    spec_file.write_text(
        f"# 3 Amigos Task\n\n## Original Request\n{task}\n\n"
        f"## Architecture & Spec (from Archie)\n{archie_spec}\n",
        encoding="utf-8",
    )

    prompt = (
        "Implement the task described in `.amigos_task.md`. "
        "Read the file first, then build a complete, production-ready implementation "
        "following the architecture spec. Run tests before finishing. "
        "End with: git add -A && git commit -m 'feat: implement via 3 Amigos'"
    )

    if progress_callback:
        mode = f"`{GITHUB_REPO}`" if GITHUB_REPO else "local sandbox"
        await progress_callback(
            f"🚀 *Claude Code is now running* in {mode}\n"
            f"Branch: `{branch}` • I'll post progress every 4 operations"
        )

    # Run Claude Code -- this is where the real work happens
    cc_result = await _run_claude_code(build_dir, prompt, progress_callback)

    # Push + open PR
    pr_url = await _create_pr(build_dir, branch, task)

    # Build the summary report
    built_files = sorted(
        str(p.relative_to(build_dir))
        for p in build_dir.rglob("*")
        if p.is_file() and not any(
            part.startswith(".") for part in p.parts[len(build_dir.parts):]
        )
    )
    file_list = "\n".join(f"  - `{f}`" for f in built_files[:40])
    if len(built_files) > 40:
        file_list += f"\n  _...and {len(built_files) - 40} more_"

    summary = (
        f"### 🔨 Claude Code Build Complete\n\n"
        f"*{len(built_files)} files* • Branch: `{branch}`\n\n"
        f"*Files created:*\n{file_list}\n\n"
        f"*Claude Code summary:*\n{cc_result}"
    )

    # Clean up local sandbox once code is safely in GitHub
    if GITHUB_REPO and pr_url:
        shutil.rmtree(build_dir, ignore_errors=True)

    return summary, pr_url
