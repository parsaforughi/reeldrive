import logging
from pathlib import Path

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


def _login_client(
    username: str,
    password: str,
    session_path: Path,
    *,
    session_id: str = "",
    proxy: str = "",
) -> Client | None:
    username = (username or "").strip().lstrip("@")
    if not username:
        return None

    proxy = proxy or settings.instagram_proxy
    session_path.parent.mkdir(parents=True, exist_ok=True)
    client = Client()
    _apply_proxy(client, proxy)

    # 1) Session ID from env (best for Railway — login once on your PC)
    sid = (session_id or "").strip()
    if sid:
        try:
            client.login_by_sessionid(sid)
            client.dump_settings(session_path)
            client.get_timeline_feed()
            logger.info("Instagram OK via session id: @%s", client.username or username)
            return client
        except Exception as exc:
            logger.error("Session ID login failed for @%s: %s", username, exc)

    # 2) Saved session file (no password if still valid)
    if session_path.exists():
        try:
            client.load_settings(session_path)
            client.get_timeline_feed()
            logger.info("Instagram OK via saved session: @%s", client.username or username)
            return client
        except LoginRequired:
            logger.info("Saved session expired for @%s", username)
        except Exception as exc:
            logger.warning("Could not reuse session file %s: %s", session_path, exc)

    # 3) Password login (often blocked on cloud IPs)
    if not password:
        logger.error(
            "No valid session for @%s. Set password or run locally:\n"
            "  python scripts/ig_export_session.py",
            username,
        )
        return None

    try:
        client.login(username, password)
        client.dump_settings(session_path)
        client.get_timeline_feed()
        logger.info("Instagram OK via password: @%s", username)
        return client
    except BadPassword:
        logger.error(
            "Instagram blocked or wrong password for @%s. "
            "Cloud server IPs are often blacklisted — export session on your PC:\n"
            "  python scripts/ig_export_session.py\n"
            "Then upload sessions/bridge.json to Railway volume.",
            username,
        )
    except TwoFactorRequired:
        logger.error(
            "2FA on @%s — disable 2FA temporarily or export session locally.",
            username,
        )
    except ChallengeRequired:
        logger.error(
            "Instagram security challenge for @%s — open IG app, confirm login, "
            "then run scripts/ig_export_session.py on your PC.",
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

        self.bridge = _login_client(
            bridge_login,
            bridge_pass,
            session_file,
            session_id=session_id,
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
