# 3 Amigos — AI Engineering Team in Slack

A single `@amigos` Slack bot that runs three specialist AI agents in sequence, each with its own personality and a human approval gate between phases.

| Agent | Persona | Model | Superpower |
|-------|---------|-------|------------|
| 🧠 **Archie** | AI Architect & Researcher | `claude-opus-4-6` | Deep research + Mermaid architecture diagrams |
| 🔨 **Builder** | AI Coder | `claude-sonnet-4-6` | Production-grade code generation |
| 📊 **Eval** | AI Evaluator & Red Teamer | `claude-sonnet-4-6` | LLM-as-judge + red-teaming + metrics |

## Workflow

```
You:      @amigos Build a RAG pipeline with Claude + Pinecone
                            │
                    ┌───────▼────────┐
                    │  🧠 Archie     │  researches → posts architecture + Mermaid + spec
                    └───────┬────────┘
                            │  ← you react 👍 or click Approve
                    ┌───────▼────────┐
                    │  🔨 Builder    │  implements → posts complete code
                    └───────┬────────┘
                            │  ← you react 👍 or click Approve
                    ┌───────▼────────┐
                    │  📊 Eval       │  tests → posts metrics + red-team findings
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
SLACK_BOT_TOKEN=xoxb-...          # from OAuth & Permissions
SLACK_SIGNING_SECRET=...           # from Basic Information
ANTHROPIC_API_KEY=sk-ant-...       # your Claude Max API key
TAVILY_API_KEY=tvly-...            # optional — free at tavily.com (gives Archie live web search)
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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

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
├── workflow.py           # LangGraph graph: Archie → Builder → Eval → Summary
├── config.py             # All env-var config in one place
│
├── agents/
│   ├── archie.py         # Research + architecture (claude-opus-4-6, web search tool)
│   ├── builder.py        # Code generation (claude-sonnet-4-6, 16k token budget)
│   └── evaluator.py      # LLM-as-judge + red-teaming (claude-sonnet-4-6)
│
├── tools/
│   ├── slack_poster.py   # post_as_archie/builder/eval + Block Kit approval buttons
│   └── search.py         # Tavily web search (used by Archie)
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

    LangGraph --> ArchieNode["🧠 archie_node"]
    ArchieNode -->|tool_use| TavilySearch["🔍 Tavily Web Search"]
    ArchieNode -->|chat_postMessage| SlackAPI

    LangGraph --> BuilderNode["🔨 builder_node"]
    BuilderNode -->|chat_postMessage| SlackAPI

    LangGraph --> EvalNode["📊 eval_node"]
    EvalNode -->|chat_postMessage| SlackAPI

    LangGraph --> SummaryNode["✅ summary_node"]

    ArchieNode -->|claude-opus-4-6| AnthropicAPI["Anthropic API"]
    BuilderNode -->|claude-sonnet-4-6| AnthropicAPI
    EvalNode -->|claude-sonnet-4-6| AnthropicAPI
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent orchestration | LangGraph | Built-in `interrupt()` + SQLite checkpointing = rock-solid human-in-the-loop |
| Web framework | FastAPI + Slack Bolt | Async-native; Bolt handles Slack signature verification |
| State persistence | SQLite (2 DBs) | Zero-ops; works on free hosting tiers; checkpoints survive restarts |
| Archie's model | `claude-opus-4-6` | Best reasoning for architecture decisions; justified cost for one-time design phase |
| Builder/Eval model | `claude-sonnet-4-6` | Fast + capable; cost-efficient for longer code/eval outputs |
| Approval UX | Block Kit buttons + 👍 + keywords | Three options so the engineer can approve however feels natural |
| Message chunking | Auto-split at 2 800 chars | Slack's 3 000-char limit; splits on newlines cleanly |

---

## Customisation

### Swap models
Edit `config.py`:
```python
ARCHIE_MODEL = "claude-opus-4-6"    # or "claude-sonnet-4-6" to save cost
BUILDER_MODEL = "claude-sonnet-4-6"
EVAL_MODEL = "claude-sonnet-4-6"
```

### Add tools to Builder
In `agents/builder.py`, add Anthropic `tool_use` definitions (e.g., `read_file`, `run_tests`).
The Builder already uses the standard agentic loop pattern from Archie — just extend it.

### Add more agents
Add a new node function in `workflow.py`, register it in `build_graph()`, and add a `post_as_*`
function in `tools/slack_poster.py`.

---

## License

MIT
