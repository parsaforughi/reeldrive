#!/usr/bin/env python3
"""
Log in to Instagram on YOUR computer and save session for Railway.

Ways to authenticate:
  A) Username/email + password (may need 2FA code)
  B) Browser sessionid cookie (no password API login)

  export INSTAGRAM_BRIDGE_LOGIN="email_or_username"
  export INSTAGRAM_BRIDGE_PASSWORD="password"
  python3 scripts/ig_export_session.py

  # Or from browser cookie sessionid:
  export INSTAGRAM_BRIDGE_SESSION_ID="paste_sessionid_cookie"
  python3 scripts/ig_export_session.py
"""

import os
import re
import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    TwoFactorRequired,
)


def _clean(value: str) -> str:
    return unquote(value.strip().strip(""""\u201c\u201d'"""))


def _sessionid_login(client: Client, sessionid: str) -> None:
    user_id = re.search(r"^\d+", sessionid)
    if not user_id:
        raise ValueError("sessionid must start with numeric user id")
    uid = user_id.group()
    cookies: dict[str, str] = {"sessionid": sessionid}
    for key, env in (
        ("csrftoken", "INSTAGRAM_BRIDGE_CSRFTOKEN"),
        ("mid", "INSTAGRAM_BRIDGE_MID"),
    ):
        val = os.environ.get(env, "").strip()
        if val:
            cookies[key] = val
    client.settings["cookies"] = cookies
    client.init()
    client.authorization_data = {
        "ds_user_id": uid,
        "sessionid": sessionid,
        "should_use_header_over_cookies": True,
    }
    client.cookie_dict["ds_user_id"] = uid
    login = os.environ.get("INSTAGRAM_BRIDGE_LOGIN", "").strip().lstrip("@")
    if login:
        client.username = login


def _validate_session(client: Client) -> None:
    try:
        client.direct_threads(5)
    except Exception:
        client.get_timeline_feed()


def _login_with_password(client: Client, username: str, password: str) -> None:
    verification = os.environ.get("INSTAGRAM_2FA_CODE", "").strip()
    try:
        if verification:
            client.login(username, password, verification_code=verification)
        else:
            client.login(username, password)
    except TwoFactorRequired:
        print("\n2FA is enabled on this account.")
        code = os.environ.get("INSTAGRAM_2FA_CODE", "").strip()
        if not code:
            code = input("Enter 6-digit code from SMS / Authenticator app: ").strip()
        if not code:
            print("Set INSTAGRAM_2FA_CODE=123456 and run again.")
            sys.exit(1)
        client.login(username, password, verification_code=code)
    except ChallengeRequired as exc:
        print("\nInstagram wants a security check.")
        print("1. Open Instagram app or instagram.com and confirm it was you")
        print("2. Wait 2 minutes and run this script again")
        print(f"Detail: {exc}")
        sys.exit(1)


def main() -> None:
    session_path = Path(
        os.environ.get("INSTAGRAM_BRIDGE_SESSION_PATH", "sessions/bridge.json")
    )
    session_id = _clean(os.environ.get("INSTAGRAM_BRIDGE_SESSION_ID", ""))

    session_path.parent.mkdir(parents=True, exist_ok=True)
    client = Client()

    if session_id:
        print("Using INSTAGRAM_BRIDGE_SESSION_ID from browser cookie…")
        _sessionid_login(client, session_id)
        try:
            _validate_session(client)
            print(f"Session OK for @{client.username or '?'}")
        except Exception as exc:
            print(
                f"Warning: API check failed ({exc!r}) — still saving {session_path}.\n"
                "If bridge fails on Railway: open Instagram app → confirm security alert,\n"
                "then re-copy sessionid + csrftoken + mid (see docs/BRIDGE_SETUP_FA.md)."
            )
        client.dump_settings(session_path)
        print(f"OK — session saved to {session_path}")
        return

    username = _clean(
        os.environ.get("INSTAGRAM_BRIDGE_LOGIN")
        or os.environ.get("INSTAGRAM_BRIDGE_USERNAME")
        or os.environ.get("INSTAGRAM_USERNAME")
        or ""
    )
    password = os.environ.get("INSTAGRAM_BRIDGE_PASSWORD") or os.environ.get(
        "INSTAGRAM_PASSWORD"
    )

    if not username:
        print("Set INSTAGRAM_BRIDGE_LOGIN (email or IG username)")
        sys.exit(1)
    if not password:
        password = getpass("Instagram password: ")

    print(f"Logging in as {username!r} …")
    print("Tip: if this fails, use EMAIL login or browser sessionid (see docs/BRIDGE_SETUP_FA.md)")

    try:
        _login_with_password(client, username, password)
    except BadPassword:
        print(
            "\nLogin failed (BadPassword). Try:\n"
            "  1. Log in on instagram.com with the SAME login — is it email not @reeldrivebot?\n"
            "  2. Put email in ig_export_local.sh: INSTAGRAM_BRIDGE_LOGIN=you@email.com\n"
            "  3. If 2FA: INSTAGRAM_2FA_CODE=123456 ./scripts/ig_export_local.sh\n"
            "  4. Or skip password — copy sessionid cookie from browser (docs/BRIDGE_SETUP_FA.md)\n"
            "  5. Wait a few hours if IG blocked too many attempts\n"
        )
        sys.exit(1)

    client.dump_settings(session_path)
    print(f"OK — session saved to {session_path}")
    print("Upload to Railway volume: /app/sessions/bridge.json")
    if client.sessionid:
        print(f"\n(Optional) INSTAGRAM_BRIDGE_SESSION_ID={client.sessionid}")


if __name__ == "__main__":
    main()
