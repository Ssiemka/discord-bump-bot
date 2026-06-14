"""
Single-run bump script for GitHub Actions.
Reads config from environment variables set in the workflow.
"""

import asyncio
import aiohttp
import os
import time
import random
import sys

TOKEN      = os.environ["DISCORD_TOKEN"]
GUILD_ID   = os.environ["GUILD_ID"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
SERVER     = os.environ.get("SERVER_NAME", "Server")

DISBOARD_APP_ID = "302050872383242240"

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


async def main():
    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/application-command-index"
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                print(f"Failed to fetch commands: HTTP {resp.status}")
                sys.exit(1)
            data = await resp.json()

        cmd = next(
            (c for c in data.get("application_commands", [])
             if c.get("application_id") == DISBOARD_APP_ID and c.get("name") == "bump"),
            None
        )
        if not cmd:
            print(f"bump command not found in {SERVER}.")
            sys.exit(1)

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
                print(f"Bumped {SERVER} successfully!")
            else:
                body = await resp.text()
                print(f"Bump failed: HTTP {resp.status} - {body}")
                sys.exit(1)


asyncio.run(main())
