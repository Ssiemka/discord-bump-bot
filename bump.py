"""
Single-run bump script for GitHub Actions.
Reads config from environment variables set in the workflow.

Before bumping, checks DISBOARD's last message in the channel to ensure
the 2-hour cooldown has expired. Waits if it hasn't — so it always succeeds
regardless of GitHub Actions startup timing variation.
"""

import asyncio
import aiohttp
import os
import time
import random
import sys
from datetime import datetime, timezone

TOKEN      = os.environ["DISCORD_TOKEN"]
GUILD_ID   = os.environ["GUILD_ID"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
SERVER     = os.environ.get("SERVER_NAME", "Server")

DISBOARD_APP_ID = "302050872383242240"
COOLDOWN_SECS   = 7230  # 2h0m30s — 30s buffer above DISBOARD's 2h cooldown

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def nonce():
    return str(int(time.time() * 1000) - random.randint(0, 500))


def session_id():
    return "".join(random.choices("0123456789abcdef", k=32))


async def get_seconds_since_last_disboard_msg(session):
    """
    Scan recent channel messages for DISBOARD's last message.
    Returns seconds since that message, or None if not found.
    """
    url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages?limit=50"
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            print(f"[{SERVER}] Could not read channel messages: {resp.status}")
            return None
        messages = await resp.json()

    for msg in messages:
        if msg.get("author", {}).get("id") != DISBOARD_APP_ID:
            continue
        ts_str = msg.get("timestamp", "")
        try:
            msg_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        elapsed = (datetime.now(timezone.utc) - msg_time).total_seconds()
        print(f"[{SERVER}] Last DISBOARD message was {elapsed:.0f}s ago.")
        return elapsed

    print(f"[{SERVER}] No DISBOARD message found in last 50 messages.")
    return None


async def wait_for_cooldown(session):
    """Wait until DISBOARD's 2h cooldown has expired."""
    elapsed = await get_seconds_since_last_disboard_msg(session)

    if elapsed is None:
        print(f"[{SERVER}] No cooldown reference found — proceeding immediately.")
        return

    if elapsed >= COOLDOWN_SECS:
        print(f"[{SERVER}] Cooldown cleared ({elapsed:.0f}s >= {COOLDOWN_SECS}s).")
        return

    wait = COOLDOWN_SECS - elapsed
    print(f"[{SERVER}] Cooldown active — waiting {wait:.0f}s ({wait/60:.1f} min)...")
    await asyncio.sleep(wait)
    print(f"[{SERVER}] Done waiting. Bumping now.")


async def main():
    async with aiohttp.ClientSession() as session:

        # Step 1: wait for cooldown if needed
        await wait_for_cooldown(session)

        # Step 2: fetch /bump command
        cmd_url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/application-command-index"
        async with session.get(cmd_url, headers=HEADERS) as resp:
            if resp.status != 200:
                print(f"[{SERVER}] Failed to fetch commands: HTTP {resp.status}")
                sys.exit(1)
            data = await resp.json()

        cmd = next(
            (c for c in data.get("application_commands", [])
             if c.get("application_id") == DISBOARD_APP_ID and c.get("name") == "bump"),
            None,
        )
        if not cmd:
            print(f"[{SERVER}] /bump command not found.")
            sys.exit(1)

        # Step 3: send bump
        payload = {
            "type": 2,
            "application_id": DISBOARD_APP_ID,
            "guild_id": GUILD_ID,
            "channel_id": CHANNEL_ID,
            "session_id": session_id(),
            "data": {
                "version": cmd["version"],
                "id": cmd["id"],
                "name": "bump",
                "type": 1,
                "options": [],
                "attachments": [],
            },
            "nonce": nonce(),
        }

        async with session.post(
            "https://discord.com/api/v9/interactions",
            headers=HEADERS,
            json=payload,
        ) as resp:
            if resp.status == 204:
                print(f"[{SERVER}] Bumped successfully!")
            else:
                body = await resp.text()
                print(f"[{SERVER}] Bump failed: HTTP {resp.status} — {body}")
                sys.exit(1)


asyncio.run(main())
