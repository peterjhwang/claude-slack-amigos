# Contributing to 3 Amigos

Thanks for your interest! This project welcomes contributions of all kinds.

## Ways to Contribute

- **Bug reports** — use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature ideas** — use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
- **Code** — see the workflow below
- **Docs** — README improvements, examples, tutorials always welcome

---

## Development Setup

```bash
# 1. Fork + clone
git clone https://github.com/<your-fork>/claude-slack-amigos
cd claude-slack-amigos

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env template and fill in your keys
cp .env.example .env
# edit .env with your SLACK_BOT_TOKEN, ANTHROPIC_API_KEY, etc.

# 5. Run locally
uvicorn main:app --reload --port 3000

# 6. Expose to Slack with ngrok (for testing)
ngrok http 3000
```

---

## Project Structure

```
main.py           — Slack Bolt + FastAPI event handlers
workflow.py       — LangGraph graph (Archie → Builder → Eval)
agents/
  archie.py       — Research agent (claude-opus-4-6 + web search)
  builder.py      — Claude Code CLI subprocess integration
  evaluator.py    — LLM-as-judge evaluation
tools/
  slack_poster.py — Persona-aware Slack posting
  search.py       — Tavily web search
state/manager.py  — SQLite state management
```

---

## Submitting a Pull Request

1. **Open an issue first** for non-trivial changes — avoids duplicate work
2. Branch off `main`: `git checkout -b feat/my-feature`
3. Keep changes focused — one feature or fix per PR
4. Ensure `python -c "import ast; ast.parse(open('main.py').read())"` passes for any Python files you touch (CI will check this)
5. Update `README.md` if you add new env vars or change the setup flow
6. Fill in the PR template when opening

---

## Agent Development Guidelines

When modifying or adding agents:

- **Archie** (`agents/archie.py`) — uses `claude-opus-4-6`. Keep the tool-use loop pattern; add new tools to `_TOOLS`.
- **Builder** (`agents/builder.py`) — delegates to the `claude` CLI subprocess. Don't add in-process tool calls here — extend the prompt instead.
- **Eval** (`agents/evaluator.py`) — uses `claude-sonnet-4-6`. Keep the LLM-as-judge pattern; the scorecard format is important for Eval's UX.
- **New agent** — add a node in `workflow.py`, a `post_as_<name>` helper in `tools/slack_poster.py`, and a persona in `config.py`.

---

## Code Style

- Python 3.12+, type hints throughout
- Async/await for all I/O
- `logging` module — no `print()` in production paths
- No hardcoded secrets — everything via `config.py` from env vars
- Comments only where logic is non-obvious

---

## Questions?

Open a [Discussion](https://github.com/CrazyCatapultCollective/claude-slack-amigos/discussions) or drop into the issue tracker.
