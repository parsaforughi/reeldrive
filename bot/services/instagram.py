import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from bot.config import settings
from bot.services.cdn_download import download_cdn_url
from bot.services.hikerapi import hiker_client

logger = logging.getLogger(__name__)
TMP = Path("/tmp/reeldrive")


@dataclass
class ProfileResult:
    username: str
    full_name: str
    biography: str
    follower_count: int
    following_count: int
    media_count: int
    is_private: bool
    is_verified: bool
    profile_pic_path: Path
    direct_urls: list[str] = field(default_factory=list)


@dataclass
class StoryItem:
    path: Path
    is_video: bool
    taken_at: str
    direct_url: str = ""


@dataclass
class MediaResult:
    paths: list[Path]
    caption: str
    media_type: str
    direct_urls: list[str] = field(default_factory=list)
    post_meta: object | None = None  # PostMeta when available
    source_url: str = ""


@dataclass
class HighlightInfo:
    pk: str
    title: str
    item_count: int


@dataclass
class FollowUser:
    username: str
    full_name: str
    is_private: bool
    is_verified: bool


def _best_image_url(item: dict) -> str:
    versions = item.get("image_versions") or []
    if isinstance(versions, list):
        for candidate in versions:
            if isinstance(candidate, dict) and candidate.get("url"):
                return str(candidate["url"])
    return str(item.get("thumbnail_url") or "")


def _media_url(item: dict) -> tuple[str, bool] | None:
    """Return (direct_url, is_video) for a photo/video/story media dict."""
    is_video = item.get("media_type") == 2
    url = item.get("video_url") if is_video else _best_image_url(item)
    if not url:
        url = item.get("thumbnail_url")
    if not url:
        return None
    return str(url), is_video


def _format_taken_at(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    if "T" in text:
        date_part, _, rest = text.partition("T")
        return f"{date_part} {rest[:5]}"
    return text


class InstagramDownloader:
    def _ensure_tmp(self) -> Path:
        TMP.mkdir(parents=True, exist_ok=True)
        return TMP

    async def _download_story_items(self, items: list[dict]) -> list[StoryItem]:
        folder = self._ensure_tmp()
        result: list[StoryItem] = []
        async with aiohttp.ClientSession() as session:
            for i, item in enumerate(items):
                resolved = _media_url(item)
                if not resolved:
                    continue
                url, is_video = resolved
                path = await download_cdn_url(session, url, folder, i, is_video=is_video)
                if not path:
                    continue
                result.append(
                    StoryItem(
                        path=path,
                        is_video=is_video,
                        taken_at=_format_taken_at(item.get("taken_at")),
                        direct_url=url,
                    )
                )
        return result

    async def get_stories(self, username: str) -> list[StoryItem]:
        stories = await hiker_client.fetch_user_stories(username)
        if not stories:
            return []
        return await self._download_story_items(stories)

    async def list_highlights(self, username: str) -> list[HighlightInfo]:
        highlights = await hiker_client.fetch_user_highlights(username)
        result: list[HighlightInfo] = []
        for h in highlights or []:
            pk = str(h.get("pk") or h.get("id") or "")
            if not pk:
                continue
            items = h.get("items") or []
            count = h.get("media_count")
            if count is None:
                count = len(items)
            result.append(
                HighlightInfo(
                    pk=pk, title=h.get("title") or "Highlight", item_count=int(count or 0)
                )
            )
        return result

    async def download_highlight_by_index(self, username: str, index: int) -> list[StoryItem]:
        highlights = await hiker_client.fetch_user_highlights(username)
        if index < 1 or index > len(highlights):
            raise ValueError(
                f"هایلایت #{index} وجود ندارد. تعداد: {len(highlights)}"
            )
        return await self._download_story_items(highlights[index - 1].get("items") or [])

    async def download_media_url(self, url: str) -> MediaResult:
        media = await hiker_client.fetch_media_by_url(url)
        if not media:
            raise ValueError("پست پیدا نشد / Media not found")

        folder = self._ensure_tmp()
        media_type = media.get("media_type")
        paths: list[Path] = []
        direct_urls: list[str] = []

        async with aiohttp.ClientSession() as session:
            sources = media.get("resources") or [media] if media_type == 8 else [media]
            for i, source in enumerate(sources):
                resolved = _media_url(source)
                if not resolved:
                    continue
                m_url, is_video = resolved
                path = await download_cdn_url(session, m_url, folder, i, is_video=is_video)
                if path:
                    paths.append(path)
                    direct_urls.append(m_url)

        if not paths:
            raise ValueError("فایلی برای دانلود نیست / Nothing to download")

        type_names = {1: "photo", 2: "video", 8: "album"}
        return MediaResult(
            paths=paths,
            caption=media.get("caption_text") or "",
            media_type=type_names.get(media_type, "media"),
            direct_urls=direct_urls,
        )

    async def zip_stories(self, username: str) -> Path:
        stories = await self.get_stories(username)
        if not stories:
            raise ValueError("استوری فعالی نیست / No active stories")
        return self._zip_paths([s.path for s in stories], f"{username}_stories.zip")

    async def zip_posts(self, username: str, limit: int | None = None) -> Path:
        limit = limit or settings.max_zip_posts
        medias = await hiker_client.fetch_user_medias(username, limit)
        folder = self._ensure_tmp()
        paths: list[Path] = []
        idx = 0
        async with aiohttp.ClientSession() as session:
            for media in medias:
                sources = (
                    media.get("resources") or [media]
                    if media.get("media_type") == 8
                    else [media]
                )
                for source in sources:
                    resolved = _media_url(source)
                    if not resolved:
                        continue
                    m_url, is_video = resolved
                    path = await download_cdn_url(session, m_url, folder, idx, is_video=is_video)
                    idx += 1
                    if path:
                        paths.append(path)
        if not paths:
            raise ValueError("پستی دانلود نشد / No posts downloaded")
        return self._zip_paths(paths, f"{username}_posts.zip")

    async def search_hashtag(self, tag: str, amount: int = 12) -> list[str]:
        medias = await hiker_client.fetch_hashtag_medias(tag.lstrip("#"), amount)
        links = []
        for m in medias or []:
            code = m.get("code")
            if code:
                links.append(f"https://www.instagram.com/p/{code}/")
        return links

    def _zip_paths(self, paths: list[Path], name: str) -> Path:
        zip_path = self._ensure_tmp() / name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, p in enumerate(paths):
                if p.exists():
                    zf.write(p, arcname=f"{i+1}{p.suffix}")
        return zip_path


instagram_downloader = InstagramDownloader()
