"""Read Instagram DMs via the web private API (www.instagram.com).

instagrapi uses the mobile API (i.instagram.com) with a fake Android device,
which Instagram rejects for browser session ids (HTTP 467 / "Prompt has
contribution" 4415001). The web endpoint accepts the browser `sessionid`
cookie directly, so we use it for the DM bridge.
"""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

import requests

logger = logging.getLogger(__name__)

WEB_APP_ID = "936619743392459"
WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
INBOX_URL = "https://www.instagram.com/api/v1/direct_v2/inbox/"
BADGE_URL = "https://www.instagram.com/api/v1/direct_v2/get_badge_count/"


@dataclass
class WebDMItem:
    item_id: str
    user_id: str
    text: str
    item_type: str
    is_sent_by_viewer: bool
    media_url: str = ""  # built from a shared reel/post (item_type clip/media_share)


def _build_media_url(code: str, media_type) -> str:
    kind = "reel" if str(media_type) == "2" else "p"
    return f"https://www.instagram.com/{kind}/{code}/"


def _find_code(obj) -> tuple[str, object] | None:
    """Depth-first search for a media shortcode in a shared item payload."""
    if isinstance(obj, dict):
        code = obj.get("code")
        if isinstance(code, str) and code:
            return code, obj.get("media_type")
        for value in obj.values():
            found = _find_code(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_code(value)
            if found:
                return found
    return None


def _extract_share_url(raw_item: dict) -> str:
    """Extract an instagram.com URL from a shared reel/post/clip DM item."""
    item_type = raw_item.get("item_type") or ""
    share_keys = (
        "clip",
        "media_share",
        "story_share",
        "felix_share",
        "reel_share",
        "xma_media_share",
        "xma_clip",
    )
    if item_type not in share_keys and not any(k in raw_item for k in share_keys):
        return ""
    for key in share_keys:
        container = raw_item.get(key)
        if container:
            found = _find_code(container)
            if found:
                code, media_type = found
                return _build_media_url(code, media_type)
    return ""


@dataclass
class WebDMThread:
    thread_id: str
    users: dict[str, str] = field(default_factory=dict)  # pk -> username
    items: list[WebDMItem] = field(default_factory=list)


class WebDMClient:
    def __init__(self, sessionid: str, ds_user_id: str, proxy: str = "") -> None:
        self.sessionid = unquote((sessionid or "").strip())
        self.ds_user_id = str(ds_user_id or "").strip()
        if not self.ds_user_id:
            m = re.match(r"^(\d+)", self.sessionid)
            self.ds_user_id = m.group(1) if m else ""
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": WEB_UA,
                "X-IG-App-ID": WEB_APP_ID,
                "Cookie": f"sessionid={self.sessionid}; ds_user_id={self.ds_user_id}",
                "Referer": "https://www.instagram.com/direct/inbox/",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        if proxy:
            self._session.proxies.update({"http": proxy, "https": proxy})

    def is_alive(self) -> bool:
        """True if the web DM API accepts this session."""
        try:
            r = self._session.get(
                INBOX_URL,
                params={"limit": "1", "thread_message_limit": "1"},
                timeout=20,
            )
            return r.status_code == 200 and "inbox" in r.json()
        except Exception as exc:
            logger.warning("Web DM session check failed: %s", exc)
            return False

    def fetch_threads(
        self, limit: int = 20, thread_message_limit: int = 10
    ) -> list[WebDMThread]:
        params = {
            "visual_message_return_type": "unseen",
            "thread_message_limit": str(thread_message_limit),
            "persistentBadging": "true",
            "limit": str(limit),
        }
        r = self._session.get(INBOX_URL, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()
        raw_threads = data.get("inbox", {}).get("threads", []) or []

        threads: list[WebDMThread] = []
        for raw in raw_threads:
            tid = str(raw.get("thread_id") or "")
            if not tid:
                continue
            users: dict[str, str] = {}
            for u in raw.get("users", []) or []:
                pk = str(u.get("pk") or u.get("id") or "")
                if pk:
                    users[pk] = u.get("username")
            items: list[WebDMItem] = []
            for it in raw.get("items", []) or []:
                items.append(
                    WebDMItem(
                        item_id=str(it.get("item_id") or it.get("message_id") or ""),
                        user_id=str(it.get("user_id") or ""),
                        text=(it.get("text") or "").strip(),
                        item_type=str(it.get("item_type") or ""),
                        is_sent_by_viewer=bool(it.get("is_sent_by_viewer")),
                        media_url=_extract_share_url(it),
                    )
                )
            threads.append(WebDMThread(thread_id=tid, users=users, items=items))
        return threads
