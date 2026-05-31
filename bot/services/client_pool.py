import json
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
from bot.services.ig_web_dm import WebDMClient

logger = logging.getLogger(__name__)


def _session_credentials(session_id_env: str, session_path: Path) -> tuple[str, str]:
    """Return (sessionid, ds_user_id) from env var or dumped session file."""
    sid = unquote((session_id_env or "").strip())
    if sid:
        m = re.match(r"^(\d+)", sid)
        return sid, (m.group(1) if m else "")
    if session_path.exists():
        try:
            data = json.loads(session_path.read_text())
            auth = data.get("authorization_data") or {}
            sid = auth.get("sessionid") or (data.get("cookies") or {}).get("sessionid", "")
            uid = str(auth.get("ds_user_id") or "")
            if sid and not uid:
                m = re.match(r"^(\d+)", sid)
                uid = m.group(1) if m else ""
            return sid, uid
        except Exception as exc:
            logger.warning("Could not read sessionid from %s: %s", session_path, exc)
    return "", ""


def _apply_proxy(client: Client, proxy: str) -> None:
    if proxy:
        client.set_proxy(proxy)
        logger.info("Instagram proxy enabled")


def _apply_sessionid(client: Client, session_id: str, username: str) -> None:
    """Sessionid only — no extra cookies, no user_info API."""
    sid = unquote(session_id.strip())
    match = re.search(r"^\d+", sid)
    if not match:
        raise ValueError("INSTAGRAM_BRIDGE_SESSION_ID must start with user id digits")
    uid = match.group()
    client.settings["cookies"] = {"sessionid": sid}
    client.init()
    client.authorization_data = {
        "ds_user_id": uid,
        "sessionid": sid,
        "should_use_header_over_cookies": True,
    }
    client.cookie_dict["ds_user_id"] = uid
    client.username = (username or "bridge").lstrip("@")


def _try_validate_inbox(client: Client) -> bool:
    try:
        client.direct_threads(3)
        return True
    except Exception as exc:
        logger.warning("Inbox check failed (session may still work): %s", exc)
        return False


def _login_client(
    username: str,
    password: str,
    session_path: Path,
    *,
    session_id: str = "",
    proxy: str = "",
    allow_password_login: bool = True,
    trust_session_on_connect: bool = False,
) -> Client | None:
    username = (username or "bridge").strip().lstrip("@")
    proxy = proxy or settings.instagram_proxy
    session_path.parent.mkdir(parents=True, exist_ok=True)
    sid = unquote((session_id or "").strip())

    if sid:
        client = Client()
        client.delay_range = [1, 3]
        _apply_proxy(client, proxy)
        try:
            _apply_sessionid(client, sid, username)
            client.dump_settings(session_path)
            if trust_session_on_connect:
                logger.info(
                    "Bridge session loaded from INSTAGRAM_BRIDGE_SESSION_ID (@%s)",
                    client.username,
                )
                return client
            if _try_validate_inbox(client):
                logger.info("Instagram OK via session id: @%s", client.username)
                return client
            logger.error(
                "Session id rejected by Instagram API. Get a fresh sessionid from "
                "browser (logged in as reeldrivebot) or set INSTAGRAM_PROXY."
            )
            return None
        except Exception as exc:
            logger.error("Invalid INSTAGRAM_BRIDGE_SESSION_ID: %s", exc)
            return None

    if session_path.exists():
        client = Client()
        client.delay_range = [1, 3]
        _apply_proxy(client, proxy)
        try:
            client.load_settings(session_path)
            if trust_session_on_connect or _try_validate_inbox(client):
                logger.info("Instagram OK via saved session: @%s", client.username or username)
                return client
        except LoginRequired:
            logger.info("Saved session expired for @%s", username)
        except Exception as exc:
            logger.warning("Could not reuse session file %s: %s", session_path, exc)

    if not allow_password_login or not password:
        return None

    client = Client()
    client.delay_range = [1, 3]
    _apply_proxy(client, proxy)
    try:
        client.login(username, password)
        client.dump_settings(session_path)
        if _try_validate_inbox(client):
            logger.info("Instagram OK via password: @%s", username)
            return client
    except BadPassword:
        logger.error("Instagram blocked password login for @%s — use INSTAGRAM_BRIDGE_SESSION_ID", username)
    except TwoFactorRequired:
        logger.error("2FA on @%s — use INSTAGRAM_BRIDGE_SESSION_ID", username)
    except ChallengeRequired:
        logger.error("Challenge on @%s — use INSTAGRAM_BRIDGE_SESSION_ID", username)
    except Exception:
        logger.exception("Instagram login failed for @%s", username)
    return None


class ClientPool:
    def __init__(self) -> None:
        self.service: Client | None = None
        self.bridge: Client | None = None
        self.bridge_web: WebDMClient | None = None
        self.bridge_inbox_ok: bool = False

    @property
    def service_ready(self) -> bool:
        return self.service is not None

    @property
    def bridge_ready(self) -> bool:
        """Session loaded (may still fail to read DMs on cloud IP)."""
        return self.bridge is not None

    @property
    def bridge_dm_ready(self) -> bool:
        """Can read @reeldrivebot inbox (needs session + IP Instagram accepts)."""
        return self.bridge is not None and self.bridge_inbox_ok

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
            logger.info("Service IG skipped — no session file")
            return False
        self.service = _login_client(
            user,
            settings.instagram_password,
            session_file,
            session_id=settings.instagram_session_id,
        )
        return self.service is not None

    def connect_bridge(self) -> bool:
        session_id = (settings.instagram_bridge_session_id or "").strip()
        session_file = settings.bridge_session_file
        public_handle = settings.bridge_ig_handle

        if not session_id and not session_file.exists():
            if not settings.instagram_bridge_force_login:
                logger.info(
                    "Bridge IG skipped — set INSTAGRAM_BRIDGE_SESSION_ID (one variable). "
                    "Handle: %s",
                    public_handle,
                )
                self.bridge = None
                return False

        bridge_login = (
            settings.instagram_bridge_login
            or settings.instagram_bridge_username
            or settings.instagram_bridge_display
            or settings.instagram_username
            or "reeldrivebot"
        ).strip().lstrip("@")

        bridge_pass = (
            settings.instagram_bridge_password or settings.instagram_password or ""
        )
        allow_password = bool(bridge_pass) and not session_id

        self.bridge_inbox_ok = False
        self.bridge_web = None
        self.bridge = _login_client(
            bridge_login,
            bridge_pass,
            session_file,
            session_id=session_id,
            allow_password_login=allow_password,
            trust_session_on_connect=bool(session_id),
        )
        if not self.bridge:
            return False

        # DM reading uses the web API (www.instagram.com) — the mobile API that
        # instagrapi uses is rejected for browser session ids (467 / prompt 4415001).
        sid, uid = _session_credentials(session_id, session_file)
        if sid:
            web = WebDMClient(sid, uid, proxy=settings.instagram_proxy)
            if web.is_alive():
                self.bridge_web = web
                self.bridge_inbox_ok = True
                logger.info(
                    "Bridge IG ready (web DM API) — DMs to %s will forward to "
                    "connected Telegram users",
                    public_handle,
                )
                return True

        # Fallback: try instagrapi mobile inbox (rarely works with browser session)
        self.bridge_inbox_ok = _try_validate_inbox(self.bridge)
        if self.bridge_inbox_ok:
            logger.info(
                "Bridge IG ready (mobile API) — DMs to %s will forward",
                public_handle,
            )
        else:
            logger.error(
                "Bridge session loaded but Instagram blocks the DM inbox. "
                "Refresh INSTAGRAM_BRIDGE_SESSION_ID (log in as %s in a browser, "
                "copy the sessionid cookie). Bio+/verify and Telegram links still work.",
                public_handle,
            )
        return True

    def get_download_client(self, use_connected: bool = False) -> Client:
        if self.service:
            return self.service
        raise RuntimeError("Instagram service not connected")


client_pool = ClientPool()
