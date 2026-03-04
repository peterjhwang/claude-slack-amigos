#!/usr/bin/env python3
"""
Test script to verify Slack URL verification works correctly.
This simulates what Slack sends during event subscription setup.
"""
import asyncio
import json
import hmac
import hashlib
import time
from httpx import AsyncClient

# You'll need to replace these with your actual values
SLACK_SIGNING_SECRET = ""  # Get from .env
TEST_URL = "http://localhost:3000/slack/events"  # Your ngrok or local URL


def generate_slack_signature(timestamp: str, body: bytes, signing_secret: str) -> str:
    """Generate Slack request signature for verification."""
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


async def test_url_verification():
    """Test if your endpoint handles Slack's url_verification correctly."""

    # This is what Slack sends during Event Subscriptions setup
    challenge_payload = {
        "token": "Jhj5dZrVaK7ZwHHjRyZWjbDl",  # Slack's verification token
        "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P",
        "type": "url_verification"
    }

    body = json.dumps(challenge_payload).encode()
    timestamp = str(int(time.time()))

    if not SLACK_SIGNING_SECRET:
        print("⚠️  SLACK_SIGNING_SECRET not set. Skipping signature generation.")
        print("Update this script with your signing secret from .env\n")
        signature = "v0=fakesignature"
    else:
        signature = generate_slack_signature(timestamp, body, SLACK_SIGNING_SECRET)

    headers = {
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }

    print(f"🧪 Testing URL verification at: {TEST_URL}")
    print(f"📤 Sending challenge request...")

    async with AsyncClient() as client:
        try:
            response = await client.post(TEST_URL, content=body, headers=headers, timeout=10.0)

            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response body: {response.text}\n")

            if response.status_code == 200:
                # Slack expects the challenge value to be returned
                response_data = response.json()
                if response_data.get("challenge") == challenge_payload["challenge"]:
                    print("✅ URL verification PASSED!")
                    print("Your endpoint correctly handles url_verification.")
                    return True
                else:
                    print("❌ URL verification FAILED!")
                    print(f"Expected challenge: {challenge_payload['challenge']}")
                    print(f"Got: {response_data}")
                    return False
            else:
                print("❌ URL verification FAILED!")
                print(f"Expected 200, got {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Request failed: {e}")
            print("\nTroubleshooting:")
            print("1. Is your server running? (uvicorn main:app --port 3000)")
            print("2. If using ngrok, update TEST_URL to your ngrok URL")
            print("3. Check your firewall/network settings")
            return False


async def main():
    print("=" * 60)
    print("Slack Event Subscriptions - URL Verification Test")
    print("=" * 60)
    print()

    success = await test_url_verification()

    if success:
        print("\n" + "=" * 60)
        print("Next steps:")
        print("1. Go to https://api.slack.com/apps → Your App → Event Subscriptions")
        print("2. Enable Events: Toggle ON")
        print(f"3. Request URL: {TEST_URL}")
        print("4. Subscribe to bot events:")
        print("   - app_mention")
        print("   - message.channels")
        print("   - message.groups")
        print("   - message.im")
        print("   - message.mpim")
        print("   - reaction_added")
        print("5. Save Changes")
        print("=" * 60)


if __name__ == "__main__":
    # Load SLACK_SIGNING_SECRET from .env if available
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
    except ImportError:
        pass

    asyncio.run(main())
