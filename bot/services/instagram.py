import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from instagrapi import Client
from instagrapi.exceptions import ClientError, MediaNotFound, PrivateError, UserNotFound

from bot.config import settings
from bot.services.client_pool import client_pool

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


@dataclass
class HighlightInfo:
    pk: str
    title: str
    item_count: int


class InstagramDownloader:
    def _client(self) -> Client:
        return client_pool.get_download_client()

    def _ensure_tmp(self) -> Path:
        TMP.mkdir(parents=True, exist_ok=True)
        return TMP

    def get_profile(self, username: str) -> ProfileResult:
        client = self._client()
        try:
            user_id = client.user_id_from_username(username)
            info = client.user_info(user_id)
        except UserNotFound as exc:
            raise ValueError("کاربر پیدا نشد / User not found") from exc
        except PrivateError as exc:
            raise ValueError(
                "اکانت پرایوت — برای دسترسی پیجت را متصل کن / Private account"
            ) from exc

        pic_url = str(info.profile_pic_url_hd or info.profile_pic_url)
        folder = self._ensure_tmp()
        downloaded = client.photo_download_by_url(
            pic_url, folder=str(folder), filename=f"{username}_profile"
        )
        actual = Path(downloaded)
        if not actual.exists():
            candidates = sorted(
                folder.glob(f"{username}_profile*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                actual = candidates[0]

        return ProfileResult(
            username=info.username,
            full_name=info.full_name or "",
            biography=info.biography or "",
            follower_count=info.follower_count or 0,
            following_count=info.following_count or 0,
            media_count=info.media_count or 0,
            is_private=bool(info.is_private),
            is_verified=bool(info.is_verified),
            profile_pic_path=actual,
            direct_urls=[pic_url],
        )

    def get_stories(self, username: str) -> list[StoryItem]:
        client = self._client()
        try:
            user_id = client.user_id_from_username(username)
            stories = client.user_stories(user_id)
        except UserNotFound as exc:
            raise ValueError("کاربر پیدا نشد / User not found") from exc
        except PrivateError as exc:
            raise ValueError("اکانت پرایوت / Private account") from exc

        folder = self._ensure_tmp()
        items: list[StoryItem] = []
        for story in stories or []:
            try:
                path = Path(client.story_download(story.pk, folder=str(folder)))
                is_video = story.media_type == 2
                taken = (
                    story.taken_at.strftime("%Y-%m-%d %H:%M") if story.taken_at else ""
                )
                url = ""
                if hasattr(story, "video_url") and story.video_url:
                    url = str(story.video_url)
                elif hasattr(story, "thumbnail_url") and story.thumbnail_url:
                    url = str(story.thumbnail_url)
                items.append(
                    StoryItem(path=path, is_video=is_video, taken_at=taken, direct_url=url)
                )
            except ClientError:
                logger.warning("Story download failed %s", story.pk)
        return items

    def list_highlights(self, username: str) -> list[HighlightInfo]:
        client = self._client()
        user_id = client.user_id_from_username(username)
        highlights = client.user_highlights(user_id)
        return [
            HighlightInfo(
                pk=str(h.pk),
                title=h.title or "Highlight",
                item_count=len(h.item_ids or []),
            )
            for h in highlights or []
        ]

    def download_highlight(self, username: str, highlight_pk: str) -> list[StoryItem]:
        client = self._client()
        folder = self._ensure_tmp()
        items: list[StoryItem] = []
        highlight = client.highlight_info(highlight_pk)
        try:
            paths = client.highlight_download(highlight_pk, folder=str(folder))
            for path in paths:
                items.append(
                    StoryItem(
                        path=Path(path),
                        is_video=str(path).endswith(".mp4"),
                        taken_at=highlight.title or "",
                    )
                )
        except ClientError:
            logger.warning("Highlight download failed %s", highlight_pk)
        return items

    def download_highlight_by_index(self, username: str, index: int) -> list[StoryItem]:
        highlights = self.list_highlights(username)
        if index < 1 or index > len(highlights):
            raise ValueError(
                f"هایلایت #{index} وجود ندارد. تعداد: {len(highlights)}"
            )
        return self.download_highlight(username, highlights[index - 1].pk)

    def download_media_url(self, url: str) -> MediaResult:
        client = self._client()
        try:
            media_pk = client.media_pk_from_url(url)
            media = client.media_info(media_pk)
        except MediaNotFound as exc:
            raise ValueError("پست پیدا نشد / Media not found") from exc

        folder = self._ensure_tmp()
        paths: list[Path] = []
        direct_urls: list[str] = []

        if media.media_type == 8:
            album_files = client.album_download(media_pk, folder=str(folder))
            paths = [Path(p) for p in album_files]
        else:
            paths.extend(self._download_media_item(client, media, folder))

        direct_urls.extend(self._extract_direct_urls(media))

        if not paths:
            raise ValueError("فایلی برای دانلود نیست / Nothing to download")

        type_names = {1: "photo", 2: "video", 8: "album"}
        return MediaResult(
            paths=paths,
            caption=media.caption_text or "",
            media_type=type_names.get(media.media_type, "media"),
            direct_urls=direct_urls,
        )

    def zip_stories(self, username: str) -> Path:
        stories = self.get_stories(username)
        if not stories:
            raise ValueError("استوری فعالی نیست / No active stories")
        return self._zip_paths(
            [s.path for s in stories], f"{username}_stories.zip"
        )

    def zip_posts(self, username: str, limit: int | None = None) -> Path:
        client = self._client()
        limit = limit or settings.max_zip_posts
        user_id = client.user_id_from_username(username)
        medias = client.user_medias(user_id, amount=limit)
        folder = self._ensure_tmp()
        paths: list[Path] = []
        for media in medias:
            try:
                if media.media_type == 8:
                    paths.extend(
                        Path(p)
                        for p in client.album_download(media.pk, folder=str(folder))
                    )
                else:
                    paths.extend(self._download_media_item(client, media, folder))
            except ClientError:
                continue
        if not paths:
            raise ValueError("پستی دانلود نشد / No posts downloaded")
        return self._zip_paths(paths, f"{username}_posts.zip")

    def search_hashtag(self, tag: str, amount: int = 12) -> list[str]:
        client = self._client()
        name = tag.lstrip("#")
        medias = client.hashtag_medias_recent(name, amount=amount)
        links = []
        for m in medias:
            code = m.code
            if code:
                links.append(f"https://www.instagram.com/p/{code}/")
        return links

    def _download_media_item(
        self, client: Client, media: Any, folder: Path
    ) -> list[Path]:
        paths: list[Path] = []
        if media.media_type == 2:
            paths.append(Path(client.video_download(media.pk, folder=str(folder))))
        elif media.media_type == 1:
            paths.append(Path(client.photo_download(media.pk, folder=str(folder))))
        return paths

    def _extract_direct_urls(self, media: Any) -> list[str]:
        urls: list[str] = []
        for attr in ("video_url", "thumbnail_url"):
            val = getattr(media, attr, None)
            if val:
                urls.append(str(val))
        resources = getattr(media, "resources", None) or []
        for res in resources:
            for attr in ("video_url", "thumbnail_url"):
                val = getattr(res, attr, None)
                if val:
                    urls.append(str(val))
        return list(dict.fromkeys(urls))

    def _zip_paths(self, paths: list[Path], name: str) -> Path:
        zip_path = self._ensure_tmp() / name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, p in enumerate(paths):
                if p.exists():
                    zf.write(p, arcname=f"{i+1}{p.suffix}")
        return zip_path


instagram_downloader = InstagramDownloader()


class InstagramServiceFacade:
    @property
    def is_ready(self) -> bool:
        return client_pool.service_ready

    def connect(self) -> bool:
        return client_pool.connect_service()

    def get_profile(self, username: str) -> ProfileResult:
        return instagram_downloader.get_profile(username)

    def get_stories(self, username: str) -> list[StoryItem]:
        return instagram_downloader.get_stories(username)

    def download_media_url(self, url: str) -> MediaResult:
        return instagram_downloader.download_media_url(url)


instagram_service = InstagramServiceFacade()
