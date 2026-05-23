import re
from urllib.parse import urlparse

USERNAME_RE = re.compile(r"^@?([a-zA-Z0-9._]{1,30})$")

INSTAGRAM_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

PROFILE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]{1,30})/?(?:\?.*)?$",
    re.IGNORECASE,
)

RESERVED_PATHS = {
    "p",
    "reel",
    "reels",
    "tv",
    "stories",
    "explore",
    "accounts",
    "direct",
    "about",
    "legal",
}


def parse_username(text: str) -> str | None:
    text = text.strip()
    if not text or " " in text:
        return None
    if INSTAGRAM_URL_RE.search(text):
        return None
    match = PROFILE_URL_RE.match(text)
    if match:
        name = match.group(1).lower()
        if name in RESERVED_PATHS:
            return None
        return name
    match = USERNAME_RE.match(text)
    if match:
        return match.group(1).lower()
    return None


def parse_media_url(text: str) -> str | None:
    text = text.strip()
    match = INSTAGRAM_URL_RE.search(text)
    if match:
        return normalize_instagram_url(text)
    return None


def normalize_instagram_url(text: str) -> str:
    if not text.startswith("http"):
        text = "https://" + text.lstrip("/")
    parsed = urlparse(text)
    return f"https://www.instagram.com{parsed.path}".rstrip("/") + "/"
