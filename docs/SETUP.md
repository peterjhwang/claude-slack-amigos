# Setup Guide

This guide walks you through setting up the 3 Amigos Slack bot from scratch.

## Prerequisites

- **Python 3.12+**
- **Slack workspace** where you can create apps
- **Anthropic API key** (for Claude models)
- Optional: GitHub token, Jira credentials, Tavily API key

---

## Step 1: Create Your Slack App

### 1.1 Create the App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. **App Name**: `3 Amigos` (or whatever you prefer)
4. **Workspace**: Select your workspace
5. Click **"Create App"**

### 1.2 Configure OAuth Scopes

Navigate to **OAuth & Permissions** in the left sidebar.

Scroll down to **"Bot Token Scopes"** and add these scopes:

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Detect when someone mentions `@amigos` |
| `chat:write` | Send messages as the bot |
| `chat:write.customize` | Post with custom usernames & emojis (for agent personas) |
| `reactions:read` | Detect 👍 reactions for approvals |
| `channels:history` | Read thread messages in public channels |
| `groups:history` | Read thread messages in private channels |
| `im:history` | Read direct messages |
| `mpim:history` | Read group direct messages |
| `files:write` | Upload files (code zips, reports) |
| `users:read` | Read user info |

### 1.3 Install to Workspace

1. Scroll to the top of the **OAuth & Permissions** page
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-...`)
   - ⚠️ Keep this secret! You'll add it to `.env` later

### 1.4 Get Signing Secret

1. Navigate to **"Basic Information"** in the left sidebar
2. Scroll to **"App Credentials"**
3. Click **"Show"** next to **Signing Secret**
4. **Copy the signing secret**

### 1.5 Configure Event Subscriptions

1. Navigate to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to **ON**
3. In **"Request URL"**, enter:
   ```
   https://your-domain.com/slack/events
   ```
   
   📝 **Note**: If you're testing locally, you'll need to expose your localhost using **ngrok** (see Step 4 below). For now, you can skip this and come back after starting your server.

4. Scroll to **"Subscribe to bot events"** and add:
   - `app_mention`
   - `message.channels`
   - `message.groups`
   - `message.im`
   - `message.mpim`
   - `reaction_added`

5. Click **"Save Changes"**

### 1.6 Configure Interactive Components

1. Navigate to **"Interactivity & Shortcuts"** in the left sidebar
2. Toggle **"Interactivity"** to **ON**
3. In **"Request URL"**, enter:
   ```
   https://your-domain.com/slack/interactive
   ```
   
   📝 **Note**: Same domain as Event Subscriptions, just a different path

4. Click **"Save Changes"**

---

## Step 2: Get API Keys

### 2.1 Anthropic API Key (Required)

1. Go to [https://console.anthropic.com](https://console.anthropic.com)
2. Sign in or create an account
3. Navigate to **API Keys**
4. Click **"Create Key"**
5. Copy the key (starts with `sk-ant-...`)

⚠️ **Note**: The Coder agent uses Claude Code CLI, which always requires an Anthropic API key even if you use different models for other agents.

### 2.2 GitHub Token (Optional - enables automatic PRs)

1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. **Note**: `3 Amigos Bot`
4. **Scopes**: Check these boxes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Actions workflows)
5. Click **"Generate token"**
6. Copy the token (starts with `ghp_...` or `github_pat_...`)

### 2.3 Tavily API Key (Optional - enables web search for Researcher)

1. Go to [https://tavily.com](https://tavily.com)
2. Sign up for a free account
3. Navigate to **API Keys**
4. Copy your API key (starts with `tvly-...`)

**Free tier**: 1,000 searches/month (plenty for most use cases)

### 2.4 Zenrows API Key (Optional - alternative to Tavily)

1. Go to [https://www.zenrows.com](https://www.zenrows.com)
2. Sign up for an account
3. Copy your API key from the dashboard

### 2.5 Jira Credentials (Optional - enables Jira integration)

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **"Create API token"**
3. **Label**: `3 Amigos Bot`
4. Click **"Create"**
5. Copy the token

You'll also need:
- Your Jira site URL (e.g., `yourcompany.atlassian.net`)
- Your email address (tied to the API token)
- A project key where the bot can create tickets (e.g., `ENG`, `PROJ`)

---

## Step 3: Install Claude Code CLI

The **Coder agent** requires Claude Code CLI to be installed on your system.

### Install Claude Code

```bash
# Install via official script (recommended)
curl -fsSL https://claude.ai/install.sh | bash

# Verify installation
claude --version
```

**On Windows:**
```powershell
# Install via PowerShell
irm https://claude.ai/install.ps1 | iex
claude --version
```

You should see output like:
```
@anthropics/claude-code v1.x.x
```

**Note:** The bot will automatically pass your `ANTHROPIC_API_KEY` to Claude Code. You don't need to authenticate separately.

📖 **For more details**, see the [Claude Code Setup Guide](CLAUDE_CODE_SETUP.md).

---

## Step 4: Install & Configure the Bot

### 3.1 Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/claude-slack-amigos.git
cd claude-slack-amigos
```

### 3.2 Set Up Environment

**With uv (recommended - 10-100× faster):**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

**Or with standard pip:**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

**Required:**
```env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Optional (but recommended):**
```env
# GitHub - enables automatic PRs
GITHUB_TOKEN=ghp_your-token-here
GITHUB_REPO=your-org/your-repo
GITHUB_BASE_BRANCH=main

# Web Search - choose one provider
WEB_SEARCH_PROVIDER=tavily  # or "zenrows" or "basic"
TAVILY_API_KEY=tvly-your-key-here
# ZENROWS_API_KEY=your-key-here  # if using zenrows

# Jira integration
JIRA_URL=yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your-jira-token-here
JIRA_PROJECT_KEY=ENG

# Channel restrictions (optional)
# Leave empty to allow all channels
SLACK_ALLOWED_CHANNELS=C1234567890,C0987654321

# Agent customization (optional)
RESEARCHER_NAME=Archie
CODER_NAME=Builder
EVALUATOR_NAME=Eval

RESEARCHER_MODEL=claude-opus-4-6
CODER_MODEL=claude-sonnet-4-6
EVALUATOR_MODEL=claude-sonnet-4-6
```

---

## Step 5: Run the Bot

### 4.1 Start the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
```

### 4.2 Expose Localhost (for local development)

If you're running locally, you need to expose your server to the internet so Slack can reach it:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start ngrok
ngrok http 3000
```

You'll see output like:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:3000
```

**Copy the `https://` URL** (e.g., `https://abc123.ngrok.io`)

### 4.3 Update Slack App URLs

Go back to your Slack App settings:

1. **Event Subscriptions**:
   - Request URL: `https://abc123.ngrok.io/slack/events`
   - Click **"Save Changes"**
   - You should see a green ✅ checkmark

2. **Interactivity & Shortcuts**:
   - Request URL: `https://abc123.ngrok.io/slack/interactive`
   - Click **"Save Changes"**

---

## Step 6: Test the Bot

### 5.1 Invite Bot to a Channel

In Slack:
```
/invite @your-bot-name
```

### 5.2 Test a Simple Task

```
@your-bot-name Create a simple hello world function in Python
```

The bot should:
1. 🧠 **Researcher** asks scoping questions
2. You answer in the thread
3. 🧠 **Researcher** posts architecture
4. You react 👍 or click Approve
5. 🔨 **Coder** implements and opens a PR (if GitHub configured)
6. You react 👍 or click Approve
7. 📊 **Evaluator** posts test results and scorecard
8. You react 👍 or click Approve
9. ✅ All agents post summary

---

## Troubleshooting

### Bot doesn't respond to mentions

**Check:**
- ✅ Bot is invited to the channel (`/invite @bot-name`)
- ✅ Server is running (check terminal for errors)
- ✅ Event Subscriptions URL shows green ✅ in Slack settings
- ✅ `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` are correct in `.env`
- ✅ If using `SLACK_ALLOWED_CHANNELS`, make sure the channel ID is in the list

**Check logs:**
```bash
# Look for errors in your terminal where the server is running
```

### URL verification failed

**Check:**
- ✅ Server is running before saving the URL in Slack settings
- ✅ ngrok is forwarding correctly (try opening the URL in a browser)
- ✅ Firewall isn't blocking incoming requests

### "Invalid token" error

**Check:**
- ✅ You copied the **Bot User OAuth Token** (starts with `xoxb-`), not the User OAuth Token
- ✅ No extra spaces in `.env` file
- ✅ `.env` file is in the project root directory

### Agent gets stuck / doesn't continue

**Check:**
- ✅ You approved the previous agent (👍 reaction or click Approve button)
- ✅ Check database: `sqlite3 data/amigos.db "SELECT * FROM thread_states;"`
- ✅ Look for errors in server logs

### GitHub PR not created

**Check:**
- ✅ `GITHUB_TOKEN` has correct scopes (`repo`, `workflow`)
- ✅ `GITHUB_REPO` is set (e.g., `myorg/myrepo`)
- ✅ You have write access to the repository
- ✅ Check Coder's message in Slack for error details

---

## Next Steps

- 📖 Read [USAGE.md](USAGE.md) for detailed usage instructions
- 🔒 Review [SECURITY.md](../SECURITY.md) for security best practices
- 🎨 Customize agent personas and models in `.env`
- 🚀 Deploy to production (see [DEPLOYMENT.md](DEPLOYMENT.md))

---

Need help? [Open an issue](https://github.com/YOUR_ORG/claude-slack-amigos/issues) or check existing documentation!
