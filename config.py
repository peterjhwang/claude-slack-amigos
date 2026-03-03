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

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]

# ── Optional integrations ─────────────────────────────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── Paths ─────────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "3000"))
DB_PATH: str = os.getenv("DB_PATH", "./data/amigos.db")
CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "./data/checkpoints.db")

# ── Model assignments (maximise Claude Max plan) ──────────────────────────────
# Archie gets Opus for deep research & architecture design
ARCHIE_MODEL: str = "claude-opus-4-6"
# Builder gets Sonnet — fast, excellent at code generation
BUILDER_MODEL: str = "claude-sonnet-4-6"
# Eval gets Sonnet — analytical, cost-efficient for judge tasks
EVAL_MODEL: str = "claude-sonnet-4-6"

# ── Agent Slack personas ───────────────────────────────────────────────────────
# chat.postMessage allows custom username + icon so each agent looks distinct
ARCHIE_PERSONA: dict = {
    "username": "🧠 Archie (AI Architect & Researcher)",
    "icon_emoji": ":brain:",
}
BUILDER_PERSONA: dict = {
    "username": "🔨 Builder (AI Coder)",
    "icon_emoji": ":hammer:",
}
EVAL_PERSONA: dict = {
    "username": "📊 Eval (AI Evaluator & Red Teamer)",
    "icon_emoji": ":bar_chart:",
}
