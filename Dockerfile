FROM python:3.12-slim

WORKDIR /app

# ── System packages ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    gnupg \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js 22 LTS (required by Claude Code CLI) ─────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Claude Code CLI ───────────────────────────────────────────────────────────
# Builder delegates all coding tasks to this — same tool-use engine as the IDE plugin
RUN npm install -g @anthropic-ai/claude-code

# ── GitHub CLI (gh) ───────────────────────────────────────────────────────────
# Builder uses `gh pr create` to open PRs and capture the URL
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) \
        signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
        https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# ── Global git config (used by Builder's commits + PRs) ──────────────────────
RUN git config --global user.email "builder@3amigos.ai" \
    && git config --global user.name "3 Amigos Builder" \
    && git config --global init.defaultBranch main

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime data directory (SQLite DBs + build sandboxes)
RUN mkdir -p /app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "info"]
