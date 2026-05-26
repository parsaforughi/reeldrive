import logging
from pathlib import Path

from instagrapi import Client

from bot.config import settings

logger = logging.getLogger(__name__)


def _login_client(
    username: str,
    password: str,
    session_path: Path,
) -> Client | None:
    if not username or not password:
        return None

    client = Client()
    session_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if session_path.exists():
            client.load_settings(session_path)
            client.login(username, password)
            client.get_timeline_feed()
        else:
            client.login(username, password)
            client.dump_settings(session_path)
        logger.info("Instagram logged in: @%s", username)
        return client
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
        self.service = _login_client(
            settings.instagram_username,
            settings.instagram_password,
            settings.service_session_file,
        )
        return self.service is not None

    def connect_bridge(self) -> bool:
        bridge_user = (settings.instagram_bridge_username or "").strip()
        bridge_pass = settings.instagram_bridge_password or ""
        if not bridge_user or not bridge_pass:
            logger.error(
                "Bridge IG offline: set INSTAGRAM_BRIDGE_USERNAME and "
                "INSTAGRAM_BRIDGE_PASSWORD for %s",
                settings.bridge_ig_handle,
            )
            self.bridge = None
            return False
        self.bridge = _login_client(
            bridge_user,
            bridge_pass,
            settings.bridge_session_file,
        )
        return self.bridge is not None

    def get_download_client(self, use_connected: bool = False) -> Client:
        if self.service:
            return self.service
        raise RuntimeError("Instagram service not connected")


client_pool = ClientPool()
