# 3 Amigos — AI Engineering Team in Slack

[![CI](https://github.com/CrazyCatapultCollective/claude-slack-amigos/actions/workflows/ci.yml/badge.svg)](https://github.com/CrazyCatapultCollective/claude-slack-amigos/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![Powered by Claude](https://img.shields.io/badge/powered%20by-Claude%20Max-orange)](https://anthropic.com)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A single `@amigos` Slack bot that runs three specialist AI agents in sequence, each with its own configurable persona and a human approval gate between phases.

> **Demo**
>
> <!-- GIF: full @amigos workflow — interview, Archie posts architecture, engineer reacts 👍, Builder opens PR, Eval posts scorecard -->
> ![3 Amigos full workflow demo](docs/demo-full-workflow.gif)

| Agent | Default Name | Model | Superpower |
|-------|-------------|-------|------------|
| 🧠 **Researcher** | Archie | `claude-opus-4-6` | Scoping interviews + deep research + architecture design |
| 🔨 **Coder** | Builder | `claude-sonnet-4-6` | Production-grade code generation + GitHub PRs |
| 📊 **Evaluator** | Eval | `claude-sonnet-4-6` | LLM-as-judge + red-teaming + metrics scorecard |

Agent display names are fully configurable via `RESEARCHER_NAME`, `CODER_NAME`, and `EVALUATOR_NAME` in `.env`.

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Complete installation and configuration
- **[Usage Guide](docs/USAGE.md)** - How to use the bot effectively
- **[Claude Code Setup](docs/CLAUDE_CODE_SETUP.md)** - How agents use Claude Code CLI
- **[Channel Restrictions](docs/CHANNEL_RESTRICTIONS.md)** - Limit bot to specific channels
- **[All Docs](docs/)** - Full documentation index

## Workflow

```
You:      @amigos Build a RAG pipeline with Claude + Pinecone
                            │
                    ┌───────▼────────┐
                    │  🧠 Researcher │  asks 3-5 scoping questions to understand requirements
                    └───────┬────────┘
                            │  ← you answer in the thread
                    ┌───────▼────────┐
                    │  🧠 Researcher │  researches → posts architecture + Mermaid + spec
                    └───────┬────────┘
                            │  ← you react 👍 or click Approve
                    ┌───────▼────────┐
                    │  🔨 Coder      │  implements → opens GitHub PR
                    └───────┬────────┘
                            │  ← you react 👍 or click Approve
                    ┌───────▼────────┐
                    │  📊 Evaluator  │  tests → posts metrics + red-team findings
                    └───────┬────────┘
                            │  ← you react 👍 or click Approve
                    ✅ All three post final summary + sign-off
```

### Approval options (any of these work)
- Click the **👍 Approve** button in Slack
- React 👍 to the agent's message
- Type `approve`, `lgtm`, `ship it`, or `yes` in the thread

### Requesting changes
- Click **✏️ Request Changes** button, then reply: `changes: <your instructions>`
- Or type `changes: <your instructions>` directly in the thread

### Starting from a Jira ticket
```
@amigos PROJ-123
```
The bot automatically fetches the ticket summary + description and uses it as the task. After the mission completes, the Jira ticket is transitioned to **Done**.

---

## Screenshots

### 🧠 Researcher — Scoping interview
<!-- GIF: Researcher posting scoping questions, engineer answering in thread -->
![Researcher scoping interview](docs/demo-interview.gif)

### 🧠 Researcher — Architecture + Mermaid diagram
<!-- GIF: Researcher posting the research summary, Mermaid diagram, spec, and approval buttons -->
![Researcher architecture output](docs/demo-archie.gif)

### 🔨 Coder — Code generation + PR opened
<!-- GIF: Coder streaming progress updates then posting the GitHub PR link -->
![Coder opening a PR](docs/demo-builder.gif)

### 📊 Evaluator — Red-team scorecard
<!-- GIF: Evaluator posting the metrics table, red-team findings, and verdict -->
![Evaluator scorecard](docs/demo-eval.gif)

---

## 1 — Create the Slack App

1. Go to **https://api.slack.com/apps** → **Create New App** → **From scratch**
2. Name it `amigos`, pick your workspace → **Create App**

### Bot Token Scopes
In **OAuth & Permissions → Bot Token Scopes**, add:

| Scope | Why |
|-------|-----|
| `app_mentions:read` | Detect `@amigos` mentions |
| `chat:write` | Post messages |
| `chat:write.customize` | Post with custom username + emoji (the personas) |
| `reactions:read` | Detect 👍 reactions |
| `channels:history` | Read thread messages |
| `groups:history` | Read thread messages in private channels |
| `im:history` | Read DM thread messages |
| `mpim:history` | Read group DM threads |

### Install the App
**OAuth & Permissions → Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-...`)

### Event Subscriptions
In **Event Subscriptions**:
- Enable Events → set **Request URL** to `https://your-domain.com/slack/events`
- Subscribe to **Bot Events**:
  - `app_mention`
  - `message.channels`
  - `message.groups`
  - `message.im`
  - `message.mpim`
  - `reaction_added`

### Interactive Components
In **Interactivity & Shortcuts**:
- Enable → set **Request URL** to `https://your-domain.com/slack/interactive`

### Basic Information
Copy the **Signing Secret** from **Basic Information → App Credentials**.

---

## 2 — Environment Setup

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Required
SLACK_BOT_TOKEN=xoxb-...          # from OAuth & Permissions
SLACK_SIGNING_SECRET=...           # from Basic Information

# LLM provider keys — only the one(s) matching your chosen models are needed
ANTHROPIC_API_KEY=sk-ant-...       # claude-* models + Claude Code CLI (Coder)
OPENAI_API_KEY=sk-...              # gpt-*, o1-*, o3-*, o4-* models
GOOGLE_API_KEY=...                 # gemini-* models

# Optional — GitHub (enables automatic PRs)
GITHUB_TOKEN=ghp_...               # needs repo + pull_request scopes
GITHUB_REPO=myorg/my-project       # leave empty to skip push/PR
GITHUB_BASE_BRANCH=main

# Optional — Tavily (gives Researcher live web search)
TAVILY_API_KEY=tvly-...            # free tier at tavily.com

# Optional — Jira (Researcher reads/creates tickets)
JIRA_URL=yourco.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=...                 # https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_PROJECT_KEY=PROJ              # project where Researcher creates Builder tickets

# Optional — rename agent personas
RESEARCHER_NAME=Archie
CODER_NAME=Builder
EVALUATOR_NAME=Eval

# Optional — run Researcher via Claude Code CLI (uses Claude Max quota)
RESEARCHER_USE_CLAUDE_CODE=false
```

---

## 3 — Run Locally (with Docker)

```bash
# Build and start
docker compose up --build

# The server listens on http://localhost:3000
# Health check: curl http://localhost:3000/health
```

For local development with Slack, expose your local port using **ngrok**:

```bash
brew install ngrok
ngrok http 3000
# Copy the https URL and set it in Slack App settings (Event Subscriptions + Interactivity)
```

### Without Docker

**With uv (recommended — 10-100× faster than pip):**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

**Or with standard pip:**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

### Managing Dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

- **[requirements.in](requirements.in)** — Direct dependencies (edit this when adding/removing packages)
- **[requirements.txt](requirements.txt)** — Locked dependencies (auto-generated, do not edit manually)

**To add or update dependencies:**

```bash
# Edit requirements.in to add/remove packages
# Then compile to requirements.txt:
uv pip compile requirements.in -o requirements.txt

# Install the updated dependencies:
uv pip install -r requirements.txt
```

This ensures reproducible builds and makes dependency changes clear in version control.


---

## 4 — Deploy to Railway (free tier)

1. Push this repo to GitHub
2. Go to **https://railway.app** → New Project → Deploy from GitHub repo
3. Add environment variables in Railway's dashboard (same as `.env`)
4. Railway auto-detects the `Dockerfile` and builds it
5. Copy the generated public URL → paste into Slack App's Event Subscriptions + Interactivity URLs

### Deploy to Render (free tier)

1. Go to **https://render.com** → New → Web Service → connect your GitHub repo
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add env vars in Render's dashboard
5. Use the generated `onrender.com` URL in Slack App settings

> **Note:** Free tiers spin down after inactivity. The first `@amigos` after a cold start may take 30–60 s. Use Railway's paid tier or Render's paid plan for always-on.

---

## Project Structure

```
claude-slack-amigos/
├── main.py               # Slack Bolt + FastAPI entry point; all event handlers
├── workflow.py           # LangGraph graph: interview → researcher → coder → evaluator → summary
├── config.py             # All env-var config in one place (models, personas, Jira, etc.)
│
├── agents/
│   ├── researcher.py     # Scoping interview + research + architecture (claude-opus-4-6)
│   ├── coder.py          # Code generation + GitHub PR (claude-sonnet-4-6)
│   └── evaluator.py      # LLM-as-judge + red-teaming (claude-sonnet-4-6)
│
├── tools/
│   ├── slack_poster.py   # post_as_researcher/coder/evaluator + Block Kit approval buttons
│   ├── jira_client.py    # Async Jira Cloud REST API v3 client
│   └── search.py         # Tavily web search (used by Researcher)
│
├── state/
│   └── manager.py        # SQLite: thread_states + message_map tables
│
├── data/                 # Auto-created; holds SQLite databases (gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Architecture

```mermaid
graph TD
    User["👤 Engineer in Slack"] -->|@amigos task| SlackAPI

    SlackAPI -->|POST /slack/events| FastAPI
    FastAPI --> SlackBolt["Slack Bolt AsyncApp"]

    SlackBolt -->|app_mention| MentionHandler
    SlackBolt -->|reaction_added| ReactionHandler
    SlackBolt -->|approve_* button| ApproveHandler
    SlackBolt -->|message in thread| MessageHandler

    MentionHandler -->|asyncio.create_task| LangGraph
    ReactionHandler -->|resume_workflow| LangGraph
    ApproveHandler -->|resume_workflow| LangGraph
    MessageHandler -->|resume_workflow| LangGraph

    LangGraph -->|interrupt| SQLiteCheckpointer["SQLite Checkpointer\n(checkpoints.db)"]
    LangGraph -->|update_thread_phase| StateDB["State DB\n(amigos.db)"]

    LangGraph --> InterviewNode["🧠 interview_node"]
    InterviewNode -->|scoping questions| SlackAPI
    InterviewNode -->|waiting_interview phase| StateDB

    LangGraph --> ResearcherNode["🧠 researcher_node"]
    ResearcherNode -->|tool_use| TavilySearch["🔍 Tavily Web Search"]
    ResearcherNode -->|tool_use| JiraRead["🎫 Jira Read/Create"]
    ResearcherNode -->|chat_postMessage| SlackAPI

    LangGraph --> CoderNode["🔨 coder_node"]
    CoderNode -->|PR link + comment| JiraUpdate["🎫 Jira Update"]
    CoderNode -->|chat_postMessage| SlackAPI

    LangGraph --> EvalNode["📊 eval_node"]
    EvalNode -->|chat_postMessage| SlackAPI

    LangGraph --> SummaryNode["✅ summary_node"]
    SummaryNode -->|transition to Done| JiraUpdate

    ResearcherNode -->|claude-opus-4-6| AnthropicAPI["Anthropic API"]
    CoderNode -->|claude-sonnet-4-6| AnthropicAPI
    EvalNode -->|claude-sonnet-4-6| AnthropicAPI
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent orchestration | LangGraph | Built-in `interrupt()` + SQLite checkpointing = rock-solid human-in-the-loop |
| Web framework | FastAPI + Slack Bolt | Async-native; Bolt handles Slack signature verification |
| State persistence | SQLite (2 DBs) | Zero-ops; works on free hosting tiers; checkpoints survive restarts |
| Researcher's model | `claude-opus-4-6` | Best reasoning for architecture decisions; justified cost for one-time design phase |
| Coder's engine | Claude API (default) or Claude Code CLI | API mode for standard use; set `RESEARCHER_USE_CLAUDE_CODE=true` for Max quota |
| Evaluator's model | `claude-sonnet-4-6` | Fast + analytical; cost-efficient for judge tasks |
| Approval UX | Block Kit buttons + 👍 + keywords | Three options so the engineer can approve however feels natural |
| Interview gate | LangGraph `interrupt()` before research | Captures scoping context before any token spend on architecture |
| Jira integration | REST API v3 + ADF | Full ticket lifecycle: read → create (Researcher) → update (Coder) → close (Summary) |
| Message chunking | Auto-split at 2 800 chars | Slack's 3 000-char limit; splits on newlines cleanly |
| Agent names | Configurable via env vars | Rename personas without touching code |

---

## Customisation

### Rename the agents
In `.env`:
```env
RESEARCHER_NAME=Ada
CODER_NAME=Bob
EVALUATOR_NAME=Eve
```

### Swap models (including OpenAI and Gemini)

Each agent's model lives inside its persona dict in `config.py`. Change the `"model"` value — the provider is detected automatically from the model name prefix:

```python
RESEARCHER_PERSONA: dict = {
    ...
    "model": "claude-opus-4-6",       # Anthropic (default)
    # "model": "gpt-4o",              # OpenAI
    # "model": "gemini-2.0-flash",    # Google
}
EVALUATOR_PERSONA: dict = {
    ...
    "model": "claude-sonnet-4-6",     # Anthropic (default)
    # "model": "gpt-4o-mini",         # OpenAI
    # "model": "gemini-2.0-flash",    # Google
}
```

| Prefix | Provider | Required env var |
|--------|----------|-----------------|
| `claude-*` | Anthropic | `ANTHROPIC_API_KEY` |
| `gpt-*`, `o1-*`, `o3-*`, `o4-*` | OpenAI | `OPENAI_API_KEY` |
| `gemini-*` | Google | `GOOGLE_API_KEY` |

> **Note:** The Coder agent uses the Claude Code CLI (`claude --print`) and always requires `ANTHROPIC_API_KEY`, regardless of which model the other agents use.

### Use Claude Code CLI for Researcher
Set in `.env`:
```env
RESEARCHER_USE_CLAUDE_CODE=true
```
This routes Researcher through the `claude --print` CLI subprocess, consuming Claude Max quota instead of API credits.

### Add more agents
Add a new node function in `workflow.py`, register it in `build_graph()`, and add a `post_as_*` function in `tools/slack_poster.py`.

---

## Contributing

PRs and issues welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Security

This bot handles Slack tokens, Anthropic API keys, and GitHub tokens.
Please review [SECURITY.md](SECURITY.md) before deploying, and **never** commit `.env` to git.
To report a vulnerability privately, see the [security policy](SECURITY.md).

## License

[MIT](LICENSE) © 2025 Crazy Catapult Collective
