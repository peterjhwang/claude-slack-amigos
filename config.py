"""
Central configuration — loaded once at startup from environment variables.
All other modules import from here; nothing imports .env directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Slack ─────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN: str = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET: str = os.environ["SLACK_SIGNING_SECRET"]

# ── LLM provider keys ─────────────────────────────────────────────────────────
# Only the key matching your chosen model(s) is required.
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# ── Optional integrations ─────────────────────────────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── GitHub (Builder: clone → Claude Code → push → PR → Slack notification) ───
# Personal access token with `repo` + `pull_request` scopes
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
# e.g. "myorg/my-project". If empty, Builder skips push/PR and uploads a zip.
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")
# Base branch that PRs are opened against
GITHUB_BASE_BRANCH: str = os.getenv("GITHUB_BASE_BRANCH", "main")

# ── Jira (Archie: read tickets as input + create tickets for Builder) ─────────────
# Your Atlassian domain, e.g. "yourco.atlassian.net"
JIRA_URL: str = os.getenv("JIRA_URL", "")
# The email address tied to the API token
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
# API token from https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
# Project key where Archie creates Builder tickets (e.g. "PROJ")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")

# ── Archie behaviour ────────────────────────────────────────────────
# Set to "true" to run Archie via Claude Code CLI subprocess (uses Claude Max
# quota) instead of direct API calls via create_react_agent.
ARCHIE_USE_CLAUDE_CODE: bool = os.getenv("ARCHIE_USE_CLAUDE_CODE", "false").lower() == "true"

# ── Paths ─────────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "3000"))
DB_PATH: str = os.getenv("DB_PATH", "./data/amigos.db")
CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "./data/checkpoints.db")

# ── Agent personas ─────────────────────────────────────────────────────────────
# Each dict bundles everything that defines an agent: display name, Slack icon,
# and the Claude model it runs on. Override names via .env; swap models here.
_RESEARCHER_NAME: str = os.getenv("RESEARCHER_NAME", "Archie")
_CODER_NAME: str = os.getenv("CODER_NAME", "Builder")
_EVALUATOR_NAME: str = os.getenv("EVALUATOR_NAME", "Eval")

RESEARCHER_PERSONA: dict = {
    "name": _RESEARCHER_NAME,
    "username": f"🧠 {_RESEARCHER_NAME} (AI Architect & Researcher)",
    "icon_emoji": ":brain:",
    "model": "claude-opus-4-6",    # Opus for deep research & architecture design
}
CODER_PERSONA: dict = {
    "name": _CODER_NAME,
    "username": f"🔨 {_CODER_NAME} (AI Coder)",
    "icon_emoji": ":hammer:",
    "model": "claude-sonnet-4-6",  # Sonnet via Claude Code CLI; kept for reference
}
EVALUATOR_PERSONA: dict = {
    "name": _EVALUATOR_NAME,
    "username": f"📊 {_EVALUATOR_NAME} (AI Evaluator & Red Teamer)",
    "icon_emoji": ":bar_chart:",
    "model": "claude-sonnet-4-6",  # Sonnet — analytical, cost-efficient for judge tasks
}
