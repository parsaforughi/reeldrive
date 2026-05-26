import logging
import re
from pathlib import Path
from urllib.parse import unquote

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    LoginRequired,
    TwoFactorRequired,
)

from bot.config import settings

logger = logging.getLogger(__name__)


def _apply_proxy(client: Client, proxy: str) -> None:
    if proxy:
        client.set_proxy(proxy)
        logger.info("Instagram proxy enabled")


def _apply_sessionid(
    client: Client,
    session_id: str,
    username: str,
    *,
    csrftoken: str = "",
    mid: str = "",
) -> None:
    """Apply browser session without user_info API (avoids HTTP 467)."""
    sid = unquote(session_id.strip())
    match = re.search(r"^\d+", sid)
    if not match:
        raise ValueError("sessionid must start with numeric user id")
    uid = match.group()
    cookies: dict[str, str] = {"sessionid": sid}
    if csrftoken:
        cookies["csrftoken"] = csrftoken.strip()
    if mid:
        cookies["mid"] = mid.strip()
    client.settings["cookies"] = cookies
    client.init()
    client.authorization_data = {
        "ds_user_id": uid,
        "sessionid": sid,
        "should_use_header_over_cookies": True,
    }
    client.cookie_dict["ds_user_id"] = uid
    if csrftoken:
        client.cookie_dict["csrftoken"] = csrftoken.strip()
    if mid:
        client.cookie_dict["mid"] = mid.strip()
    client.username = username or None


def _validate_session(client: Client) -> None:
    """Check session via inbox only — timeline often triggers challenge on cloud IPs."""
    client.direct_threads(5)


def _login_client(
    username: str,
    password: str,
    session_path: Path,
    *,
    session_id: str = "",
    proxy: str = "",
    extra_cookies: dict[str, str] | None = None,
    allow_password_login: bool = True,
) -> Client | None:
    username = (username or "").strip().lstrip("@")
    if not username:
        return None

    proxy = proxy or settings.instagram_proxy
    session_path.parent.mkdir(parents=True, exist_ok=True)
    extra = extra_cookies or {}
    sid = unquote((session_id or "").strip())

    # 1) Session ID from env — soft apply, never login_by_sessionid (467 on user/info)
    if sid:
        client = Client()
        client.delay_range = [1, 3]
        _apply_proxy(client, proxy)
        try:
            _apply_sessionid(
                client,
                sid,
                username,
                csrftoken=extra.get("csrftoken", ""),
                mid=extra.get("mid", ""),
            )
            client.dump_settings(session_path)
            _validate_session(client)
            logger.info("Instagram OK via session id: @%s", client.username or username)
            return client
        except Exception as exc:
            logger.error(
                "Session ID invalid or blocked for @%s: %s. "
                "Open Instagram app → confirm security alert → refresh sessionid. "
                "Also set csrftoken + mid cookies if available.",
                username,
                exc,
            )
            return None

    # 2) Saved session file
    if session_path.exists():
        client = Client()
        client.delay_range = [1, 3]
        _apply_proxy(client, proxy)
        try:
            client.load_settings(session_path)
            _validate_session(client)
            logger.info("Instagram OK via saved session: @%s", client.username or username)
            return client
        except LoginRequired:
            logger.info("Saved session expired for @%s", username)
        except Exception as exc:
            logger.warning("Could not reuse session file %s: %s", session_path, exc)

    # 3) Password login (often blocked on cloud IPs)
    if not allow_password_login or not password:
        if not password and not sid:
            logger.error(
                "No valid session for @%s. Set INSTAGRAM_BRIDGE_SESSION_ID or run:\n"
                "  python scripts/ig_export_session.py",
                username,
            )
        return None

    client = Client()
    client.delay_range = [1, 3]
    _apply_proxy(client, proxy)
    try:
        client.login(username, password)
        client.dump_settings(session_path)
        _validate_session(client)
        logger.info("Instagram OK via password: @%s", username)
        return client
    except BadPassword:
        logger.error(
            "Instagram blocked or wrong password for @%s. "
            "Export session on your PC (scripts/ig_export_session.py) "
            "and set INSTAGRAM_BRIDGE_SESSION_ID on Railway.",
            username,
        )
    except TwoFactorRequired:
        logger.error("2FA on @%s — use browser sessionid instead.", username)
    except ChallengeRequired:
        logger.error(
            "Instagram security challenge for @%s — confirm in IG app, "
            "then set a fresh INSTAGRAM_BRIDGE_SESSION_ID.",
            username,
        )
    except Exception:
        logger.exception("Instagram login failed for @%s", username)
    return None


class ClientPool:
    def __init__(self) -> None:
        self.service: Client | None = None
        self.bridge: Client | None = None

    @property
    def service_ready(self) -> bool:
        return self.service is not None

    @property
    def bridge_ready(self) -> bool:
        return self.bridge is not None

    def connect_service(self) -> bool:
        user = (settings.instagram_username or "").strip()
        if not user:
            return False
        session_file = settings.service_session_file
        if (
            not settings.instagram_session_id
            and not session_file.exists()
            and not settings.instagram_bridge_force_login
        ):
            logger.info(
                "Service IG skipped — no session file (profile/stories need local export)"
            )
            return False
        self.service = _login_client(
            user,
            settings.instagram_password,
            session_file,
            session_id=settings.instagram_session_id,
        )
        return self.service is not None

    def connect_bridge(self) -> bool:
        bridge_login = (
            settings.instagram_bridge_login
            or settings.instagram_bridge_username
            or settings.instagram_username
            or ""
        ).strip().lstrip("@")
        bridge_pass = (
            settings.instagram_bridge_password or settings.instagram_password or ""
        )
        session_id = settings.instagram_bridge_session_id
        session_file = settings.bridge_session_file
        public_handle = settings.bridge_ig_handle
        extra_cookies = {
            "csrftoken": settings.instagram_bridge_csrftoken,
            "mid": settings.instagram_bridge_mid,
        }

        if not bridge_login:
            logger.info(
                "Bridge IG skipped — set INSTAGRAM_BRIDGE_LOGIN (email/username for API)"
            )
            self.bridge = None
            return False

        has_saved_session = bool(session_id) or session_file.exists()
        if not has_saved_session and not settings.instagram_bridge_force_login:
            logger.info(
                "Bridge IG skipped — no %s on server. IG DM → Telegram needs one-time "
                "session export (see docs/BRIDGE_SETUP_FA.md). Public handle: %s",
                session_file,
                public_handle,
            )
            self.bridge = None
            return False

        # If session id is set, never password-login on server (triggers challenge)
        allow_password = bool(bridge_pass) and not session_id

        self.bridge = _login_client(
            bridge_login,
            bridge_pass,
            session_file,
            session_id=session_id,
            extra_cookies=extra_cookies,
            allow_password_login=allow_password,
        )
        if self.bridge:
            logger.info(
                "Bridge IG ready — DMs to %s will forward to connected Telegram users",
                public_handle,
            )
        return self.bridge is not None

    def get_download_client(self, use_connected: bool = False) -> Client:
        if self.service:
            return self.service
        raise RuntimeError("Instagram service not connected")


client_pool = ClientPool()
