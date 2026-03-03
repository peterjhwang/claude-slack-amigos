# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes    |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Email **security@crazycatapultcollective.com** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You can expect a response within **48 hours** and a patch within **7 days** for confirmed issues.

---

## Secrets & API Keys — What This Bot Handles

This bot manages several sensitive credentials. Here's what each one can access:

| Credential | Used by | Scope |
|---|---|---|
| `ANTHROPIC_API_KEY` | All three agents + Claude Code CLI | Calls to Anthropic API — no data stored |
| `SLACK_BOT_TOKEN` | All event handlers | Read/write to your Slack workspace |
| `SLACK_SIGNING_SECRET` | Request verification | Verifies Slack webhook signatures |
| `GITHUB_TOKEN` | Builder only | Clone, push, create PRs in `GITHUB_REPO` |
| `TAVILY_API_KEY` | Archie only | Web search — queries are not persisted |

### Minimum required GitHub token scopes
```
repo          (for clone + push)
pull_requests (for gh pr create)
```
Do **not** grant `admin`, `delete_repo`, or `org` scopes.

---

## Security Hardening Checklist (for self-hosters)

Before deploying to production:

- [ ] All secrets are in `.env` — never committed (`.env` is in `.gitignore`)
- [ ] Docker volume for `/app/data` is not world-readable
- [ ] `SLACK_SIGNING_SECRET` is set — Bolt verifies every request signature
- [ ] `GITHUB_TOKEN` is a fine-grained PAT scoped to a **single** repo, not org-wide
- [ ] Builder's `/tmp/amigos-builds/` is cleaned up after each run (handled automatically)
- [ ] Your deployment platform (Railway/Render) uses encrypted env vars, not config files
- [ ] Slack App's **allowed redirect URLs** are set to your domain only
- [ ] Rotate all tokens if you suspect any exposure

---

## Known Limitations

- **Builder runs `claude --dangerously-skip-permissions`** — this is required for automation but means Claude Code will execute bash commands without confirmation. Only deploy this bot in a trusted, isolated environment.
- **Build sandboxes** are in `/tmp/amigos-builds/` — on a shared host, use a Docker volume instead.
- **SQLite databases** contain task descriptions and Slack thread IDs — no message content is stored.
