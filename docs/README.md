# Documentation

Welcome to the 3 Amigos documentation! This guide will help you set up, use, and deploy your AI engineering team in Slack.

## Getting Started

### Quick Links

- 📚 **[Setup Guide](SETUP.md)** - Complete installation and configuration instructions
- 🎯 **[Usage Guide](USAGE.md)** - How to use the bot effectively
- 🔧 **[Claude Code Setup](CLAUDE_CODE_SETUP.md)** - How agents use Claude Code CLI and authentication
- 🔒 **[Channel Restrictions](CHANNEL_RESTRICTIONS.md)** - Limit bot to specific channels

### Advanced Topics

- 🚀 **[Deployment Guide](DEPLOYMENT.md)** - Deploy to production (coming soon)
- 🔧 **[Configuration](CONFIGURATION.md)** - Detailed configuration options (coming soon)
- 🏗️ **[Architecture](ARCHITECTURE.md)** - Technical architecture deep dive (coming soon)

---

## Documentation Overview

### [SETUP.md](SETUP.md)
Complete step-by-step setup guide covering:
- Creating your Slack app
- Getting API keys (Anthropic, GitHub, Jira, Tavily)
- Installing dependencies with `uv` or `pip`
- Running locally with ngrok
- Troubleshooting common issues

**Start here if:** You're setting up the bot for the first time.

### [USAGE.md](USAGE.md)
Comprehensive usage guide including:
- Starting tasks and answering scoping questions
- Three methods for approving agents
- Requesting changes and revisions
- Jira integration workflows
- Tips for getting better results

**Start here if:** Your bot is set up and you want to learn how to use it.

### [CHANNEL_RESTRICTIONS.md](CHANNEL_RESTRICTIONS.md)
Guide to restricting bot access to specific channels:
- How to get channel IDs
- Configuring `SLACK_ALLOWED_CHANNELS`
- Understanding how filtering works

**Start here if:** You want to limit the bot to certain channels.

---

## Quick Reference

### Essential Commands

Start a task:
```
@amigos Create a REST API for user management
```

Start from Jira:
```
@amigos PROJ-123
```

Approve (any of these):
- Click **👍 Approve** button
- React 👍 to the message  
- Reply: `approve`, `lgtm`, `ship it`, or `yes`

Request changes:
- Click **✏️ Request Changes** button
- Reply: `changes: <your feedback>`

### Essential Environment Variables

```env
# Required
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
ANTHROPIC_API_KEY=sk-ant-...

# Highly Recommended
GITHUB_TOKEN=ghp_...
GITHUB_REPO=your-org/your-repo

# Optional but Useful
TAVILY_API_KEY=tvly-...
JIRA_URL=yourco.atlassian.net
JIRA_API_TOKEN=...
SLACK_ALLOWED_CHANNELS=C123,C456
```

### Agent Personas

| Agent | Default Name | Model | Role |
|-------|-------------|-------|------|
| 🧠 Researcher | Archie | opus-4 | Scoping + architecture |
| 🔨 Coder | Builder | sonnet-4 | Implementation + PRs |
| 📊 Evaluator | Eval | sonnet-4 | Testing + red-teaming |

Customize in `.env`:
```env
RESEARCHER_NAME=Ada
CODER_NAME=Bob
EVALUATOR_NAME=Eve

RESEARCHER_MODEL=claude-opus-4-6
CODER_MODEL=claude-sonnet-4-6
EVALUATOR_MODEL=claude-sonnet-4-6
```

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  You: @amigos Build a RAG pipeline with Claude + Pinecone  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │  🧠 Researcher   │
                  │  Scoping Phase   │
                  └────────┬─────────┘
                           │ (asks 3-5 questions)
                  ┌────────▼─────────┐
                  │  You: answers    │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  🧠 Researcher   │
                  │  Research Phase  │
                  └────────┬─────────┘
                           │ (posts architecture + spec)
                  ┌────────▼─────────┐
                  │  You: 👍 approve │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  🔨 Coder        │
                  │  Implementation  │
                  └────────┬─────────┘
                           │ (opens GitHub PR)
                  ┌────────▼─────────┐
                  │  You: 👍 approve │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  📊 Evaluator    │
                  │  Testing & Eval  │
                  └────────┬─────────┘
                           │ (posts scorecard)
                  ┌────────▼─────────┐
                  │  You: 👍 approve │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  ✅ Summary      │
                  │  All Done!       │
                  └──────────────────┘
```

---

## Troubleshooting

### Bot Not Responding

1. ✅ Check bot is invited to channel: `/invite @bot-name`
2. ✅ Verify server is running: Check terminal for errors
3. ✅ Check Event Subscriptions URL in Slack (should show green ✅)
4. ✅ Verify `.env` tokens are correct
5. ✅ Check `SLACK_ALLOWED_CHANNELS` if configured

### URL Verification Failed

1. ✅ Ensure server is running before saving URL in Slack
2. ✅ Check ngrok is forwarding correctly (try opening URL in browser)
3. ✅ Verify no firewall blocking incoming requests

### Agent Stuck / Not Continuing

1. ✅ Make sure you approved previous agent (👍 or button click)
2. ✅ Check database: `sqlite3 data/amigos.db "SELECT * FROM thread_states;"`
3. ✅ Look for errors in server logs

See [SETUP.md - Troubleshooting](SETUP.md#troubleshooting) for more details.

---

## Contributing

Want to improve the bot or documentation? See our main [CONTRIBUTING.md](../CONTRIBUTING.md) guide!

---

## Getting Help

- 📖 Read through the guides above
- 🐛 [Report bugs](https://github.com/YOUR_ORG/claude-slack-amigos/issues)
- 💬 [Discussions](https://github.com/YOUR_ORG/claude-slack-amigos/discussions)
- 🔒 [Security issues](../SECURITY.md)

---

**Built with ❤️ using Claude, LangGraph, and Slack**
