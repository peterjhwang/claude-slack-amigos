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

# ── Web Search & Scraping ─────────────────────────────────────────────────────
# Choose your preferred provider: "tavily", "zenrows", or "basic"
# - tavily: AI-powered search API (best for research, requires TAVILY_API_KEY)
# - zenrows: Web scraping API with JS rendering (good for scraping, requires ZENROWS_API_KEY)
# - basic: Simple HTTP fetching with httpx (free, no API key needed, limited capabilities)
WEB_SEARCH_PROVIDER: str = os.getenv("WEB_SEARCH_PROVIDER", "tavily")

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
ZENROWS_API_KEY: str = os.getenv("ZENROWS_API_KEY", "")

# ── GitHub (Coder: clone → Claude Code → push → PR → Slack notification) ───
# Personal access token with `repo` + `pull_request` scopes
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
# e.g. "myorg/my-project". If empty, Coder skips push/PR and uploads a zip.
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")
# Base branch that PRs are opened against
GITHUB_BASE_BRANCH: str = os.getenv("GITHUB_BASE_BRANCH", "main")

# ── Jira (Researcher: read tickets as input + create tickets for Coder) ─────────────
# Your Atlassian domain, e.g. "yourco.atlassian.net"
JIRA_URL: str = os.getenv("JIRA_URL", "")
# The email address tied to the API token
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
# API token from https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
# Project key where Researcher creates Coder tickets (e.g. "PROJ")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")

# ── Researcher behaviour ────────────────────────────────────────────────
# Set to "true" to run Researcher via Claude Code CLI subprocess (uses Claude Max
# quota) instead of direct API calls via create_react_agent.
RESEARCHER_USE_CLAUDE_CODE: bool = os.getenv("RESEARCHER_USE_CLAUDE_CODE", "false").lower() == "true"

# ── Paths ─────────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "3000"))
DB_PATH: str = os.getenv("DB_PATH", "./data/amigos.db")
CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "./data/checkpoints.db")

# ── Agent personas ─────────────────────────────────────────────────────────────
# Each dict bundles everything that defines an agent: display name, Slack icon,
# and the Claude model it runs on. Override names and models via .env.
_RESEARCHER_NAME: str = os.getenv("RESEARCHER_NAME", "Archie")
_CODER_NAME: str = os.getenv("CODER_NAME", "Builder")
_EVALUATOR_NAME: str = os.getenv("EVALUATOR_NAME", "Eval")

_RESEARCHER_MODEL: str = os.getenv("RESEARCHER_MODEL", "claude-opus-4-6")
_CODER_MODEL: str = os.getenv("CODER_MODEL", "claude-sonnet-4-6")
_EVALUATOR_MODEL: str = os.getenv("EVALUATOR_MODEL", "claude-sonnet-4-6")

RESEARCHER_PERSONA: dict = {
    "name": _RESEARCHER_NAME,
    "username": f"🧠 {_RESEARCHER_NAME} (AI Architect & Researcher)",
    "icon_emoji": ":brain:",
    "model": _RESEARCHER_MODEL,
}
CODER_PERSONA: dict = {
    "name": _CODER_NAME,
    "username": f"🔨 {_CODER_NAME} (AI Coder)",
    "icon_emoji": ":hammer:",
    "model": _CODER_MODEL,
}
EVALUATOR_PERSONA: dict = {
    "name": _EVALUATOR_NAME,
    "username": f"📊 {_EVALUATOR_NAME} (AI Evaluator & Red Teamer)",
    "icon_emoji": ":bar_chart:",
    "model": _EVALUATOR_MODEL,
}
