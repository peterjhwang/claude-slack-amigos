# Claude Code Setup Guide

This guide explains how the 3 Amigos bot uses Claude Code CLI and how to set up authentication.

## Table of Contents

- [How Agents Use Claude Code](#how-agents-use-claude-code)
- [Authentication Methods](#authentication-methods)
- [Installation](#installation)
- [Configuration](#configuration)
- [Choosing Between API and Claude Code CLI](#choosing-between-api-and-claude-code-cli)
- [Troubleshooting](#troubleshooting)

---

## How Agents Use Claude Code

The 3 Amigos bot can use **Claude Code CLI** (`claude --print`) in two ways:

### 1. Coder Agent (Always Uses Claude Code CLI)

The **Coder agent** always uses Claude Code CLI to implement features. This is intentional because:

- ✅ Claude Code has advanced file editing capabilities
- ✅ Better git integration
- ✅ More reliable code generation
- ✅ Can execute commands and verify results

**How it works:**

1. Coder clones your GitHub repo to `/tmp/amigos-builds/<build_id>/`
2. Writes the task spec to `.amigos_task.md`
3. Runs: `claude --print --dangerously-skip-permissions --output-format stream-json <prompt>`
4. Claude Code reads files, edits code, runs tests
5. Bot commits changes and opens a PR

**Command used:**
```bash
claude --print \
  --dangerously-skip-permissions \
  --output-format stream-json \
  "Read .amigos_task.md and implement the feature..."
```

### 2. Researcher Agent (Optional Claude Code CLI Mode)

The **Researcher agent** has two modes:

**Mode A: Direct API (Default)**
- Uses LangChain's `create_react_agent` with Anthropic API
- More control over tools (web search, Jira)
- Uses API credits/tokens

**Mode B: Claude Code CLI (Optional)**
- Set `RESEARCHER_USE_CLAUDE_CODE=true` in `.env`
- Uses Claude Max subscription quota instead of API
- Good for conserving API credits
- Runs in a temp directory with task written to `task.md`

**Command used (Mode B):**
```bash
claude --print \
  --dangerously-skip-permissions \
  --output-format stream-json \
  "Read task.md and produce architecture specification..."
```

---

## Authentication Methods

Claude Code CLI supports two authentication methods:

### Method 1: API Key (Recommended for Automation)

The bot passes your API key directly to Claude Code CLI via environment variable:

```python
env = {
    **os.environ,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
    "CLAUDE_CODE_SKIP_TELEMETRY": "1",
}
```

**How the bot does it:**
- Reads `ANTHROPIC_API_KEY` from your `.env` file
- Passes it to the subprocess environment
- Claude Code uses this API key for authentication

**This is what happens when the bot runs:**
```bash
# The bot runs this command with your API key in the environment
ANTHROPIC_API_KEY=sk-ant-your-key-here \
claude --print --output-format stream-json "..."
```

### Method 2: Claude Max Subscription (Alternative)

If you have a **Claude Pro/Max subscription**, Claude Code CLI can use that instead:

1. Run `claude auth login` on the machine where the bot runs
2. This creates `~/.config/claude/auth.json`
3. Claude Code CLI will use your subscription quota

**Trade-offs:**
- ✅ Uses subscription quota (doesn't consume API credits)
- ❌ Requires manual authentication on the server
- ❌ Session may expire and need re-authentication
- ❌ Not ideal for automated deployments

---

## Installation

### Step 1: Install Claude Code CLI

The bot requires the `claude` command to be available on your system.

**On macOS/Linux:**

```bash
# Install via official install script (recommended)
curl -fsSL https://claude.ai/install.sh | bash

# Verify installation
claude --version
```

**On Windows:**

```powershell
# Install via PowerShell
irm https://claude.ai/install.ps1 | iex

# Verify installation
claude --version
```

**Alternative (npm):**

```bash
# If you prefer npm
npm install -g @anthropics/claude-code
claude --version
```

**Via Docker (included in provided Dockerfile):**

The provided `Dockerfile` already includes Claude Code installation:

```dockerfile
# Install Claude Code CLI via official script
RUN curl -fsSL https://claude.ai/install.sh | bash

# Or alternatively via npm if Node.js is already installed
# RUN apt-get update && apt-get install -y nodejs npm && npm install -g @anthropics/claude-code
```

### Step 2: Configure API Key

Add your Anthropic API key to `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

**That's it!** The bot will automatically pass this to Claude Code CLI.

---

## Configuration

### For Coder Agent (Required)

The Coder agent always uses Claude Code, so you **must** have:

1. ✅ Claude Code CLI installed (`claude` command available)
2. ✅ `ANTHROPIC_API_KEY` set in `.env`

```env
# Required for Coder agent
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### For Researcher Agent (Optional)

Choose which mode you want:

**Option A: Direct API (Default)**

```env
# Leave empty or set to false (default)
RESEARCHER_USE_CLAUDE_CODE=false

# Uses API key directly
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

**Option B: Claude Code CLI**

```env
# Enable Claude Code CLI mode
RESEARCHER_USE_CLAUDE_CODE=true

# Still needs API key (or Claude Max auth)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

---

## Choosing Between API and Claude Code CLI

### When to Use API (Direct)

Use **direct API** (default) for Researcher when:

- ✅ You want precise control over tools and behavior
- ✅ You have plenty of API credits
- ✅ You want faster responses (no subprocess overhead)
- ✅ You're deploying to serverless/containerized environments

### When to Use Claude Code CLI

Use **Claude Code CLI** for Researcher when:

- ✅ You have a Claude Pro/Max subscription and want to use that quota
- ✅ You want to conserve API credits for production calls
- ✅ You prefer consistency (both agents use same engine)
- ✅ You're running on a dedicated server with Claude Code installed

### Cost Comparison

| Scenario | Researcher | Coder | Cost Source |
|----------|-----------|-------|-------------|
| **Default** | Direct API | Claude Code CLI | API credits + API credits |
| **Hybrid** | Claude Code CLI | Claude Code CLI | Max quota + API credits |
| **Cannot do** | ❌ API | ❌ API | Coder always needs Claude Code |

**Note:** Even with `RESEARCHER_USE_CLAUDE_CODE=true`, the Coder agent still uses Claude Code CLI with your API key.

---

## How the Bot Passes Credentials

Here's what happens under the hood:

### 1. Bot Loads Config

```python
# config.py
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
```

### 2. Agent Calls Claude Code

```python
# agents/coder.py or agents/researcher.py
env = {
    **os.environ,  # Inherit current environment
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,  # Add/override API key
    "CLAUDE_CODE_SKIP_TELEMETRY": "1",  # Disable telemetry
}

proc = await asyncio.create_subprocess_exec(
    "claude", "--print", "--output-format", "stream-json", prompt,
    cwd=working_dir,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env,  # Pass environment with API key
)
```

### 3. Claude Code Uses API Key

Claude Code CLI automatically detects `ANTHROPIC_API_KEY` in the environment and uses it for authentication.

---

## Troubleshooting

### "claude: command not found"

**Problem:** Claude Code CLI is not installed or not in PATH.

**Solution:**
```bash
# Check if installed
which claude

# If not found, install
npm install -g @anthropics/claude-code

# Verify
claude --version
```

### "Authentication failed" or "Invalid API key"

**Problem:** API key is wrong, expired, or not set.

**Solution:**
```bash
# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Verify format (should start with sk-ant-)
# Get new key from: https://console.anthropic.com
```

### "Rate limit exceeded"

**Problem:** Too many API calls in short time.

**Solution:**
- Wait a few minutes and try again
- Upgrade your Anthropic API plan
- Use `RESEARCHER_USE_CLAUDE_CODE=true` to use Max quota for Researcher

### "Permission denied" when running claude

**Problem:** `claude` command doesn't have execute permissions.

**Solution:**
```bash
# Find where claude is installed
which claude

# Make it executable
chmod +x $(which claude)
```

### Claude Code hangs or times out

**Problem:** Claude Code is waiting for input or taking too long.

**Solution:**
- The bot uses `--dangerously-skip-permissions` to avoid prompts
- Timeout is set to 600 seconds (10 minutes)
- Check server logs for specific errors

### Session expired (if using Claude Max auth)

**Problem:** `~/.config/claude/auth.json` session expired.

**Solution:**
```bash
# Re-authenticate
claude auth login

# Follow the prompts to log in again
```

---

## Docker Deployment

If you're using Docker, the `Dockerfile` already includes Claude Code:

```dockerfile
# Install Node.js and npm
RUN apt-get update && apt-get install -y nodejs npm

# Install Claude Code CLI
RUN npm install -g @anthropics/claude-code

# Verify installation
RUN claude --version
```

**Just make sure** your `.env` file has `ANTHROPIC_API_KEY` set:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

The Docker container will automatically use this API key when running Claude Code.

---

## Summary

### Quick Setup Checklist

For the bot to work properly:

- [ ] Install Claude Code CLI: `curl -fsSL https://claude.ai/install.sh | bash`
- [ ] Verify installation: `claude --version`
- [ ] Add API key to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] (Optional) Enable for Researcher: `RESEARCHER_USE_CLAUDE_CODE=true`
- [ ] Restart the bot: `uvicorn main:app --reload`

### Key Points

1. **Coder always uses Claude Code CLI** - No option to change this
2. **Researcher can use either** - API (default) or Claude Code CLI (optional)
3. **Authentication is automatic** - Bot passes API key to Claude Code
4. **API key is required** - Even if you have Claude Max subscription
5. **Claude Code must be installed** - `claude` command must be available

---

## Additional Resources

- [Claude Code Official Site](https://claude.ai/download)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Anthropic API Keys](https://console.anthropic.com)
- [Alternative: npm package](https://www.npmjs.com/package/@anthropics/claude-code)

---

**Need help?** [Open an issue](https://github.com/YOUR_ORG/claude-slack-amigos/issues) with your specific setup!
