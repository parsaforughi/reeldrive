import re
from dataclasses import dataclass
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


@dataclass
class ParsedCommand:
    kind: str
    username: str | None = None
    url: str | None = None
    index: int | None = None
    hashtag: str | None = None
    raw: str = ""


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
        name = match.group(1).lower()
        # Instagram usernames are never all-digits; reject so a stray number
        # (e.g. a token count typed outside its prompt) isn't sent to the API
        # as a username and waste a paid lookup on a guaranteed 400/404.
        if name.isdigit():
            return None
        return name
    return None


def parse_media_url(text: str) -> str | None:
    """Find post/reel URL even if the message has extra text around it."""
    text = (text or "").strip()
    match = INSTAGRAM_URL_RE.search(text)
    if not match:
        return None
    start = match.start()
    snippet = text[start:].split()[0].rstrip(".,;)")
    if not snippet.lower().startswith("http"):
        snippet = "https://" + snippet.lstrip("/")
    base = snippet.split("?")[0].rstrip("/")
    return base + "/"


def normalize_instagram_url(text: str) -> str:
    if not text.startswith("http"):
        text = "https://" + text.lstrip("/")
    parsed = urlparse(text)
    return f"https://www.instagram.com{parsed.path}".rstrip("/") + "/"


def parse_command(text: str) -> ParsedCommand | None:
    text = text.strip()
    lower = text.lower()
    raw = text

    if url := parse_media_url(text):
        return ParsedCommand(kind="media_url", url=url, raw=raw)

    if lower.startswith(("#", "hashtag ", "هشتگ ")):
        tag = text.lstrip("#").replace("هشتگ", "").replace("hashtag", "").strip()
        if tag:
            return ParsedCommand(kind="hashtag", hashtag=tag.lstrip("#"), raw=raw)

    patterns = [
        (r"^(?:highlights?|هایلایت|هایلایت‌ها)\s+@?(\w+)$", "highlights_list"),
        (r"^(?:highlight|هایلایت)\s+@?(\w+)\s+(\d+)$", "highlight_one"),
        (r"^(?:zip\s+stories?|زیپ\s+استوری)\s+@?(\w+)$", "zip_stories"),
        (r"^(?:zip\s+posts?|زیپ\s+پست)\s+@?(\w+)$", "zip_posts"),
        (r"^(?:profile|پروفایل)\s+@?(\w+)$", "profile"),
        (r"^(?:stories?|استوری)\s+@?(\w+)$", "stories"),
        (r"^(?:following|فالووینگ|فالوینگ|فالوئینگ)\s+@?(\w+)$", "following"),
    ]
    for pattern, kind in patterns:
        m = re.match(pattern, lower if "هایلایت" not in pattern else text, re.IGNORECASE)
        if not m:
            # retry with original text for unicode commands
            m = re.match(pattern.replace(r"\s+", r"\s+"), text, re.IGNORECASE)
        if m:
            groups = m.groups()
            username = parse_username(groups[0])
            if not username:
                continue
            idx = int(groups[1]) if len(groups) > 1 else None
            return ParsedCommand(
                kind=kind, username=username, index=idx, raw=raw
            )

    # simple: highlights username (two words)
    parts = text.split()
    if len(parts) == 2:
        cmd = parts[0].lower()
        user = parse_username(parts[1])
        if not user:
            return None
        if cmd in ("highlights", "هایلایت", "هایلایت‌ها"):
            return ParsedCommand(kind="highlights_list", username=user, raw=raw)
        if cmd in ("stories", "story", "استوری"):
            return ParsedCommand(kind="stories", username=user, raw=raw)
        if cmd in ("profile", "پروفایل"):
            return ParsedCommand(kind="profile", username=user, raw=raw)
        if cmd in ("following", "فالووینگ", "فالوینگ", "فالوئینگ"):
            return ParsedCommand(kind="following", username=user, raw=raw)
    if len(parts) == 3:
        cmd, user, num = parts[0].lower(), parts[1].lstrip("@").lower(), parts[2]
        if cmd in ("highlight", "هایلایت") and num.isdigit():
            return ParsedCommand(
                kind="highlight_one", username=user, index=int(num), raw=raw
            )
        if cmd.replace(" ", "") in ("zipstories",) or (
            parts[0].lower() == "zip" and parts[1].lower() in ("stories", "story")
        ):
            return ParsedCommand(kind="zip_stories", username=parts[2].lstrip("@"), raw=raw)

    if user := parse_username(text):
        return ParsedCommand(kind="profile", username=user, raw=raw)

    return None
