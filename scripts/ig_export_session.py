#!/usr/bin/env python3
"""
Log in to Instagram on YOUR computer (home IP) and save session for Railway.

Usage:
  export INSTAGRAM_BRIDGE_USERNAME=reeldrivebot
  export INSTAGRAM_BRIDGE_PASSWORD='your_password'
  python scripts/ig_export_session.py

Upload the created file to Railway volume:
  sessions/bridge.json

Or set env INSTAGRAM_BRIDGE_SESSION_ID from browser cookies (sessionid).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from instagrapi import Client  # noqa: E402


def main() -> None:
    username = (
        os.environ.get("INSTAGRAM_BRIDGE_LOGIN")
        or os.environ.get("INSTAGRAM_BRIDGE_USERNAME")
        or os.environ.get("INSTAGRAM_USERNAME")
    )
    password = os.environ.get("INSTAGRAM_BRIDGE_PASSWORD") or os.environ.get(
        "INSTAGRAM_PASSWORD"
    )
    session_path = Path(
        os.environ.get("INSTAGRAM_BRIDGE_SESSION_PATH", "sessions/bridge.json")
    )

    if not username or not password:
        print("Set INSTAGRAM_BRIDGE_LOGIN (or USERNAME) and INSTAGRAM_BRIDGE_PASSWORD")
        sys.exit(1)

    # Strip smart quotes / copy-paste junk
    username = username.strip().strip(""""\u201c\u201d'""")
    password = password.strip().strip(""""\u201c\u201d'""")

    session_path.parent.mkdir(parents=True, exist_ok=True)
    client = Client()
    print(f"Logging in as {username!r} …")
    print("(Use email or IG username — not the Telegram bot name unless that's your IG login)")
    client.login(username, password)
    client.dump_settings(session_path)
    print(f"OK — session saved to {session_path}")
    print("Upload this file to Railway (persistent volume: /app/sessions/)")
    sid = client.sessionid
    if sid:
        print(f"\nOptional env (instead of file):\nINSTAGRAM_BRIDGE_SESSION_ID={sid}")


if __name__ == "__main__":
    main()
