# Slack Event Subscriptions Troubleshooting Guide

## Problem: Can't save Event Subscriptions even though URL verified

This happens when Slack's URL verification succeeds, but the configuration doesn't save. Here are the most common causes and solutions:

---

## ✅ Quick Checklist

1. **Server is running and publicly accessible**
   ```bash
   # Start your server
   uvicorn main:app --host 0.0.0.0 --port 3000

   # If testing locally, use ngrok
   ngrok http 3000
   ```

2. **Request URL is correct**
   - ✅ Correct: `https://your-domain.com/slack/events`
   - ✅ Correct: `https://abc123.ngrok.io/slack/events`
   - ❌ Wrong: `https://your-domain.com/slack/events/` (trailing slash)
   - ❌ Wrong: `http://` (must be HTTPS for production)

3. **Bot Token Scopes are configured**
   - Go to: https://api.slack.com/apps → Your App → **OAuth & Permissions**
   - Required Bot Token Scopes:
     - `app_mentions:read` - To receive @mentions
     - `channels:history` - To read messages in public channels
     - `groups:history` - To read messages in private channels
     - `im:history` - To read direct messages
     - `mpim:history` - To read group DMs
     - `reactions:read` - To receive reaction events
     - `chat:write` - To post messages
     - `chat:write.customize` - To post as different usernames (Archie, Builder, Eval)

4. **Reinstall your app after scope changes**
   - After adding scopes, go to **Install App** → **Reinstall to Workspace**
   - This generates a new `SLACK_BOT_TOKEN` - update your `.env`!

---

## 🔍 Common Issues

### Issue #1: "We had trouble connecting to your URL"

**Cause**: Server not reachable or taking too long to respond.

**Solutions**:
- Check server logs for errors during startup
- Verify your lifespan context manager completes quickly
- Test with the diagnostic script:
  ```bash
  python test_slack_url.py
  ```

### Issue #2: "Your URL didn't respond with the challenge parameter"

**Cause**: Slack Bolt handler not processing url_verification correctly.

**Solutions**:
- Make sure you're NOT consuming `req.body()` before calling `handler.handle(req)`
- Verify Slack Bolt is installed: `pip show slack-bolt`
- Check that `AsyncSlackRequestHandler` is initialized correctly:
  ```python
  handler = AsyncSlackRequestHandler(slack_app)
  ```

### Issue #3: URL verifies but "Save Changes" doesn't work

**Cause**: Missing required OAuth scopes or Slack API issues.

**Solutions**:
1. Check all required bot scopes are added (see checklist above)
2. Reinstall the app to Workspace
3. Wait 1-2 minutes and try again (Slack API can be slow)
4. Try a different browser or clear browser cache

### Issue #4: "Invalid signing secret"

**Cause**: `SLACK_SIGNING_SECRET` in `.env` doesn't match your Slack app.

**Solutions**:
- Go to: https://api.slack.com/apps → Your App → **Basic Information**
- Copy **Signing Secret** and update `.env`:
  ```bash
  SLACK_SIGNING_SECRET=your_signing_secret_here
  ```
- Restart your server

---

## 🧪 Testing URL Verification

### Method 1: Use the test script
```bash
# Edit test_slack_url.py and set:
# - SLACK_SIGNING_SECRET (from .env)
# - TEST_URL (your server URL)

python test_slack_url.py
```

### Method 2: Check Slack's verification manually
1. Start your server with debug logging:
   ```bash
   export LOG_LEVEL=DEBUG
   uvicorn main:app --host 0.0.0.0 --port 3000 --log-level debug
   ```

2. In Slack App settings → Event Subscriptions → Request URL, enter your URL

3. Watch server logs for:
   ```
   INFO:slack_bolt:Received url_verification request
   ```

### Method 3: Manual curl test
```bash
curl -X POST https://your-domain.com/slack/events \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "challenge": "test_challenge_123"
  }'

# Should return:
# {"challenge":"test_challenge_123"}
```

---

## 📋 Event Subscriptions Setup (Step-by-Step)

1. **Go to Event Subscriptions**
   - https://api.slack.com/apps → Your App → **Event Subscriptions**

2. **Enable Events**
   - Toggle **Enable Events** to **On**

3. **Enter Request URL**
   - Enter: `https://your-domain.com/slack/events`
   - Wait for ✅ **Verified**

4. **Subscribe to Bot Events**
   Click **Subscribe to bot events** and add:
   - `app_mention` - When someone @mentions your bot
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels
   - `message.im` - Direct messages
   - `message.mpim` - Group direct messages
   - `reaction_added` - When reactions are added

5. **Save Changes**
   - Click **Save Changes** at the bottom
   - If it fails, check the troubleshooting steps above

6. **Verify Installation**
   ```bash
   # In any Slack channel where the bot is added:
   @amigos hello

   # You should see a response from the 3 Amigos bot
   ```

---

## 🐛 Debug Mode

Enable detailed logging to diagnose issues:

```python
# In main.py, change logging level temporarily:
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
```

Then restart and watch logs when Slack sends requests.

---

## 🆘 Still Having Issues?

1. **Check Slack API Status**: https://status.slack.com/
2. **Review Slack Bolt documentation**: https://slack.dev/bolt-python/
3. **Test with a minimal example**:
   ```python
   from slack_bolt.async_app import AsyncApp
   from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
   from fastapi import FastAPI, Request

   slack_app = AsyncApp(token="xoxb-...", signing_secret="...")
   app = FastAPI()
   handler = AsyncSlackRequestHandler(slack_app)

   @app.post("/slack/events")
   async def events(req: Request):
       return await handler.handle(req)
   ```

4. **Check your environment**:
   ```bash
   # Verify environment variables are loaded
   python -c "import config; print(config.SLACK_BOT_TOKEN[:10])"
   ```

---

## ✅ Success Indicators

Once everything works, you should see:

1. ✅ Green "Verified" checkmark in Slack Event Subscriptions UI
2. ✅ "Save Changes" button works without errors
3. ✅ Bot responds to `@amigos` mentions in Slack
4. ✅ Server logs show incoming events:
   ```
   INFO: Received app_mention event
   INFO: New task received: hello
   ```

---

## 📚 Related Documentation

- [Slack Events API](https://api.slack.com/apis/connections/events-api)
- [Slack Bolt Framework](https://slack.dev/bolt-python/concepts)
- [FastAPI + Slack Bolt](https://github.com/slackapi/bolt-python/tree/main/examples/fastapi)
