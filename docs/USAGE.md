# Usage Guide

Learn how to use the 3 Amigos bot effectively in your Slack workspace.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Approval Methods](#approval-methods)
- [Requesting Changes](#requesting-changes)
- [Jira Integration](#jira-integration)
- [Channel Restrictions](#channel-restrictions)
- [Agent Workflow](#agent-workflow)
- [Tips & Best Practices](#tips--best-practices)

---

## Basic Usage

### Starting a Task

Mention the bot in any channel where it's invited:

```
@amigos Create a REST API for user management with FastAPI
```

The bot will:
1. Start a threaded conversation
2. Ask 3-5 scoping questions
3. Wait for your answers

### Answering Scoping Questions

The Researcher agent will ask questions like:

> 🧠 **Archie (AI Architect & Researcher)**
> 
> To help me design the best solution, I have a few questions:
> 
> 1. What database should I use? (PostgreSQL, MySQL, SQLite, etc.)
> 2. Do you need authentication? If so, what type? (JWT, OAuth, etc.)
> 3. What user fields should be supported? (email, username, profile, etc.)
> 4. Should it include CRUD operations for all user fields?
> 5. Any specific API documentation requirements? (OpenAPI/Swagger?)

**Reply in the thread** with your answers:

```
1. PostgreSQL
2. Yes, JWT authentication
3. email, username, full_name, profile_picture, created_at
4. Yes, full CRUD
5. Yes, include OpenAPI docs
```

---

## Approval Methods

After each agent completes its phase, you need to approve before moving to the next agent.

### Method 1: Click the Approve Button

The agent will post a message with buttons:

> ✅ **Ready for review**
> 
> [ 👍 Approve ] [ ✏️ Request Changes ]

Click **👍 Approve** to continue.

### Method 2: React with 👍

React to the agent's message with a 👍 emoji.

### Method 3: Type Keywords

Reply in the thread with any of these:
- `approve`
- `lgtm` (looks good to me)
- `ship it`
- `yes`
- `go ahead`

---

## Requesting Changes

If you want the agent to revise their work:

### Method 1: Click Request Changes Button

1. Click **✏️ Request Changes**
2. The bot will ask what changes you want
3. Reply with your feedback:

```
changes: Please use Redis for caching and add rate limiting to the API
```

### Method 2: Type Directly

Reply in the thread:

```
changes: Add input validation for email addresses and include unit tests
```

The agent will revise their work based on your feedback.

---

## Jira Integration

If you've configured Jira credentials, you can start tasks directly from Jira tickets.

### Starting from a Jira Ticket

```
@amigos PROJ-123
```

The bot will:
1. Fetch the ticket from Jira
2. Use the ticket summary and description as the task
3. Post a link to the ticket in the thread
4. Continue with the normal workflow

### What Happens to the Ticket

- **During workflow**: Ticket status is tracked in the database
- **After Researcher**: Bot may create sub-tickets for implementation
- **After Coder**: Bot adds a comment with the PR link
- **After completion**: Ticket is automatically transitioned to **Done**

---

## Channel Restrictions

You can restrict the bot to specific channels using the `SLACK_ALLOWED_CHANNELS` environment variable.

### How to Get Channel IDs

1. Right-click the channel name in Slack
2. Select **"View channel details"**
3. Scroll to the bottom
4. Copy the **Channel ID** (e.g., `C1234567890`)

### Configure in `.env`

```env
# Single channel
SLACK_ALLOWED_CHANNELS=C1234567890

# Multiple channels (comma-separated)
SLACK_ALLOWED_CHANNELS=C1234567890,C0987654321,C5555555555

# All channels (default - leave empty)
SLACK_ALLOWED_CHANNELS=
```

See [CHANNEL_RESTRICTIONS.md](CHANNEL_RESTRICTIONS.md) for more details.

---

## Agent Workflow

### Phase 1: Scoping Interview (Researcher)

**What happens:**
- Researcher asks 3-5 clarifying questions
- You answer in the thread
- Bot waits for your complete answers

**Tips:**
- Answer all questions at once for faster processing
- Be specific about requirements
- Mention any constraints (time, budget, tech stack)

### Phase 2: Architecture & Research (Researcher)

**What happens:**
- Researcher analyzes requirements
- May perform web searches (if Tavily/Zenrows configured)
- Posts detailed architecture with:
  - Summary of approach
  - Mermaid diagram (if applicable)
  - Technical specifications
  - Implementation plan

**Tips:**
- Review the architecture carefully
- Request changes if something doesn't fit
- Approve when ready for implementation

### Phase 3: Implementation (Coder)

**What happens:**
- Coder clones the target repo (if GitHub configured)
- Implements the solution using Claude Code CLI
- Creates a pull request
- Posts PR link in Slack

**Without GitHub:**
- Creates code in a temporary directory
- Uploads a `.zip` file to Slack

**Tips:**
- Check the PR for code quality
- Review tests and documentation
- Request changes if needed

### Phase 4: Evaluation (Evaluator)

**What happens:**
- Evaluator parses acceptance criteria
- Reviews the implementation
- Runs red-team analysis (security, edge cases)
- Posts a scorecard with metrics

**Example scorecard:**

> 📊 **Eval (AI Evaluator & Red Teamer)**
> 
> | Criterion | Status | Score |
> |-----------|--------|-------|
> | ✅ API endpoints implemented | PASS | 10/10 |
> | ✅ JWT authentication working | PASS | 9/10 |
> | ⚠️ Input validation | PARTIAL | 7/10 |
> | ✅ OpenAPI docs generated | PASS | 10/10 |
> 
> **Red Team Findings:**
> - Missing rate limiting on auth endpoints
> - Password validation could be stronger
> 
> **Overall: 9.0/10** - Production-ready with minor improvements

**Tips:**
- Review security findings carefully
- Consider addressing red-team issues
- Approve when satisfied

### Phase 5: Summary

**What happens:**
- All three agents post a final summary
- Workflow is marked as complete
- Jira ticket is closed (if configured)

---

## Tips & Best Practices

### Getting Better Results

**Be specific in your initial request:**
❌ Bad: `@amigos build an API`
✅ Good: `@amigos Create a REST API for user management with FastAPI, PostgreSQL, and JWT auth`

**Answer scoping questions completely:**
❌ Bad: Single-word answers
✅ Good: Detailed explanations of requirements

**Use Jira integration for complex tasks:**
- Write detailed requirements in Jira
- Reference the ticket: `@amigos PROJ-123`
- Bot inherits all context from the ticket

### Managing Workflow

**Pause at any point:**
- Just don't approve - workflow stays paused
- Resume later by approving

**Request multiple changes:**
```
changes: 
1. Add Redis caching
2. Implement rate limiting
3. Include integration tests
4. Update README with deployment instructions
```

**Cancel a workflow:**
Currently, workflows don't have a cancel command. To effectively stop:
- Don't approve the next phase
- Workflow will remain paused indefinitely

### Performance Optimization

**Researcher model (claude-opus-4-6):**
- Expensive but thorough
- Good for complex architecture decisions
- Consider using `claude-sonnet-4-6` for simpler tasks

**Coder uses Claude Code CLI:**
- Set `RESEARCHER_USE_CLAUDE_CODE=true` to use Max quota instead of API
- Good if you have Claude subscription

**Web search (optional):**
- Tavily: Best for research, AI-powered
- Zenrows: Good for scraping specific sites
- Basic: Free but limited, uses DuckDuckGo

### Team Collaboration

**Multi-engineer approval:**
- Any team member can approve in the thread
- First approval moves to next phase

**Visibility:**
- All team members in the channel see progress
- Thread keeps full history
- Jira integration tracks across tools

---

## Common Workflows

### Quick Feature Implementation

```
@amigos Add a new endpoint /api/health that returns server status
```
→ Answer questions → Approve architecture → Approve code → Done

### Complex Multi-Component Task

```
@amigos PROJ-456
```
(Jira ticket has full requirements)
→ Answer clarifying questions → Review architecture → Approve → Review PR → Approve → Review tests → Done

### Research-Heavy Task

```
@amigos Research best practices for implementing real-time notifications 
in a microservices architecture and design a solution
```
→ Researcher does deep dive with web search → Posts comprehensive analysis → You decide on implementation

---

## Need Help?

- **Bot not responding?** See [SETUP.md](SETUP.md#troubleshooting)
- **Channel restrictions?** See [CHANNEL_RESTRICTIONS.md](CHANNEL_RESTRICTIONS.md)
- **Deployment?** See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Found a bug?** [Open an issue](https://github.com/YOUR_ORG/claude-slack-amigos/issues)
