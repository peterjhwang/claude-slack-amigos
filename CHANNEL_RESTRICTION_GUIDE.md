# Channel Restriction Guide

## How to Restrict Your Bot to Specific Channels

Your bot now supports channel-based restrictions so it only responds in channels you specify.

### Step 1: Get Channel ID

In Slack:
1. Right-click on the channel name
2. Select **"View channel details"**
3. Scroll to the bottom
4. Copy the **Channel ID** (looks like `C1234567890`)

### Step 2: Configure in .env

Add the channel ID(s) to your `.env` file:

```bash
# Single channel
SLACK_ALLOWED_CHANNELS=C1234567890

# Multiple channels (comma-separated)
SLACK_ALLOWED_CHANNELS=C1234567890,C0987654321,C5555555555

# All channels (leave empty or omit)
SLACK_ALLOWED_CHANNELS=
```

### Step 3: Restart Your Bot

```bash
# Stop the bot (Ctrl+C)
# Start it again
python main.py
```

### How It Works

When a channel restriction is configured:

- ✅ Bot **will respond** to `@mentions`, reactions, and messages in allowed channels
- ❌ Bot **will silently ignore** events from non-allowed channels
- 📝 Ignored events are logged: `Ignoring mention in non-allowed channel C1234567890`

### Examples

**Development/Testing** (single test channel):
```bash
SLACK_ALLOWED_CHANNELS=C07ABCDEFGH
```

**Production** (multiple team channels):
```bash
SLACK_ALLOWED_CHANNELS=C01ENGINEERING,C02DEVOPS,C03QATEST
```

**No Restrictions** (default - all channels):
```bash
SLACK_ALLOWED_CHANNELS=
# or just omit this line entirely
```

### Note

This filtering happens at the application level. The bot still needs the OAuth scopes to receive events from all channels. The filtering just makes it ignore events from non-allowed channels.

If you want to completely prevent the bot from accessing certain channels, you should not invite it to those channels in the first place.
