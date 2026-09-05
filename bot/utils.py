import base64
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

USERNAME_RE = re.compile(r"^@?([a-zA-Z0-9._]{1,30})$")

INSTAGRAM_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

STORY_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"stories/([a-zA-Z0-9._]{1,30})(?:/(?:highlight:)?(\d+))?",
    re.IGNORECASE,
)

HIGHLIGHT_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"highlights?/(?:highlight:)?(\d+)",
    re.IGNORECASE,
)

SHARE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/s/([A-Za-z0-9_=+-]+)",
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


@dataclass(frozen=True)
class StoryRef:
    kind: str
    url: str
    username: str | None = None
    media_id: str | None = None


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


def _unwrap_instagram_text(text: str) -> str:
    text = (text or "").strip()
    raw = text if "://" in text else f"https://{text.lstrip('/')}"
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if host in {"l.instagram.com", "www.l.instagram.com"}:
        target = (parse_qs(parsed.query).get("u") or [None])[0]
        if target:
            return unquote(target)
    return text


def _normalize_found_url(text: str, match: re.Match[str]) -> str:
    snippet = text[match.start() :].split()[0].rstrip(".,;)")
    if not snippet.lower().startswith("http"):
        snippet = "https://" + snippet.lstrip("/")
    return snippet.split("?")[0].rstrip("/") + "/"


def decode_instagram_share_code(code: str) -> tuple[str, str] | None:
    """Decode /s/<base64> share codes like highlight:1814… or story:99."""
    raw = (code or "").strip().rstrip("/")
    if not raw:
        return None
    padded = raw + "=" * ((4 - len(raw) % 4) % 4)
    decoded = ""
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(padded.encode()).decode("utf-8")
            break
        except (ValueError, UnicodeDecodeError):
            continue
    if ":" not in decoded:
        return None
    kind, pk = decoded.split(":", 1)
    kind = kind.strip().lower()
    pk = pk.strip()
    if not kind or not pk:
        return None
    return kind, pk


def parse_media_url(text: str) -> str | None:
    """Find post/reel/story/highlight URL even if the message has extra text."""
    text = _unwrap_instagram_text(text)
    for pattern in (INSTAGRAM_URL_RE, STORY_URL_RE, HIGHLIGHT_URL_RE, SHARE_URL_RE):
        match = pattern.search(text)
        if match:
            return _normalize_found_url(text, match)
    return None


def is_story_media_url(url: str) -> bool:
    url = _unwrap_instagram_text(url)
    return bool(
        STORY_URL_RE.search(url)
        or HIGHLIGHT_URL_RE.search(url)
        or SHARE_URL_RE.search(url)
    )


def parse_story_ref(url: str) -> StoryRef | None:
    normalized = parse_media_url(url) or _unwrap_instagram_text(url)
    match = STORY_URL_RE.search(normalized)
    if match:
        username = match.group(1).lower()
        media_id = match.group(2)
        kind = "highlight" if username == "highlights" else "story"
        return StoryRef(
            kind=kind,
            url=_normalize_found_url(normalized, match),
            username=None if kind == "highlight" else username,
            media_id=media_id,
        )
    match = HIGHLIGHT_URL_RE.search(normalized)
    if match:
        return StoryRef(
            kind="highlight",
            url=_normalize_found_url(normalized, match),
            media_id=match.group(1),
        )
    match = SHARE_URL_RE.search(normalized)
    if match:
        share_url = _normalize_found_url(normalized, match)
        decoded = decode_instagram_share_code(match.group(1))
        if decoded and decoded[0] in {"highlight", "highlights"}:
            return StoryRef(kind="highlight", url=share_url, media_id=decoded[1])
        if decoded and decoded[0] in {"story", "stories"}:
            return StoryRef(kind="story", url=share_url, media_id=decoded[1])
        return StoryRef(kind="share", url=share_url, media_id=match.group(1))
    return None


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
