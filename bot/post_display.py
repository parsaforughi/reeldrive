"""Regram-style post caption and metadata formatting."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import jdatetime

from bot.config import settings


@dataclass
class PostMeta:
    short_code: str = ""
    post_url: str = ""
    username: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    shares: int = 0
    timestamp_iso: str = ""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    post_tag: str = ""


def _format_jalali(iso_ts: str | None) -> str:
    if not iso_ts:
        now = datetime.now(timezone.utc)
    else:
        try:
            now = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        except ValueError:
            now = datetime.now(timezone.utc)
    jdt = jdatetime.datetime.fromgregorian(datetime=now.astimezone(timezone.utc))
    return jdt.strftime("%Y/%m/%d, %H:%M:%S")


def _fmt_num(n: int) -> str:
    return f"{n:,}"


def _nested_text(item: dict, parent: str, key: str) -> str:
    value = item.get(parent)
    if isinstance(value, dict):
        return str(value.get(key) or "")
    return ""


def _number(item: dict, *keys: str) -> int:
    for key in keys:
        value = item.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


def post_meta_from_item(item: dict, source_url: str) -> PostMeta:
    """Normalize a HikerAPI media item for captions and AI analysis."""
    short_code = str(
        item.get("code")
        or item.get("shortcode")
        or item.get("shortCode")
        or item.get("id")
        or item.get("pk")
        or ""
    )
    username = str(
        _nested_text(item, "user", "username")
        or _nested_text(item, "owner", "username")
        or item.get("ownerUsername")
        or item.get("username")
        or ""
    ).lstrip("@")
    post_url = str(item.get("url") or source_url)
    if short_code and "/p/" not in post_url and "/reel/" not in post_url:
        post_url = f"https://www.instagram.com/p/{short_code}/"

    tag = username or short_code
    hashtags = item.get("hashtags") or []
    if isinstance(hashtags, list):
        tags = [str(h).lstrip("#") for h in hashtags if h]
    else:
        tags = []

    caption_value = item.get("caption")
    if isinstance(caption_value, dict):
        caption_value = caption_value.get("text")
    caption = str(item.get("caption_text") or caption_value or item.get("text") or "")
    # hashtags inside caption if not in list
    if not tags and caption:
        import re

        tags = re.findall(r"#(\w+)", caption)

    return PostMeta(
        short_code=short_code,
        post_url=post_url,
        username=username,
        likes=_number(item, "like_count", "likes_count", "likesCount", "likes"),
        comments=_number(
            item, "comment_count", "comments_count", "commentsCount", "comments"
        ),
        views=_number(
            item,
            "play_count",
            "view_count",
            "video_view_count",
            "videoViewCount",
            "playCount",
        ),
        shares=_number(item, "reshare_count", "reshareCount", "sharesCount"),
        timestamp_iso=str(item.get("taken_at") or item.get("timestamp") or ""),
        caption=caption,
        hashtags=tags,
        post_tag=tag,
    )


def post_meta_from_url(source_url: str) -> PostMeta:
    import re

    m = re.search(
        r"instagram\.com/(?:reel|reels|p|tv)/([^/?#]+)/?",
        source_url,
        re.I,
    )
    code = m.group(1) if m else ""
    url = source_url if source_url.startswith("http") else ""
    if not url and code:
        url = f"https://www.instagram.com/reel/{code}/"
    return PostMeta(short_code=code, post_url=url, post_tag="DM")


def format_post_caption(meta: PostMeta, *, refreshed: bool = False) -> str:
    tag_line = f"# #{meta.post_tag}" if meta.post_tag else "#"
    date_line = f"📅 {_format_jalali(meta.timestamp_iso)}"
    user_line = (
        f'👤 <a href="https://www.instagram.com/{meta.username}/">'
        f"{meta.username}</a>"
        if meta.username
        else "👤 —"
    )
    stats = (
        f"{tag_line}\n"
        f"{date_line}\n"
        f"{user_line}\n"
        f"❤️ {_fmt_num(meta.likes)}\n"
        f"▶️ {_fmt_num(meta.views)}\n"
        f"💬 {_fmt_num(meta.comments)}\n"
        f"🔃 {_fmt_num(meta.shares)}"
    )
    body = meta.caption.strip()
    if meta.hashtags:
        hash_line = " ".join(f"#{h}" for h in meta.hashtags[:30])
        if hash_line not in body:
            body = f"{body}\n\n{hash_line}".strip() if body else hash_line

    footer = f"🔄 {_format_jalali(None)}"
    bot_footer = f"📩 @{settings.bot_mention.lstrip('@')}"

    parts = [stats]
    if body:
        parts.append(body)
    parts.append(f"{footer}\n{bot_footer}")
    text = "\n\n".join(parts)
    if len(text) > 1000:
        text = text[:997] + "…"
    return text
