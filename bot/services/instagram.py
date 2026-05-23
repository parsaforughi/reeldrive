import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from instagrapi import Client
from instagrapi.exceptions import (
    ClientError,
    LoginRequired,
    MediaNotFound,
    PrivateError,
    UserNotFound,
)

from bot.config import settings

logger = logging.getLogger(__name__)


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


@dataclass
class StoryItem:
    path: Path
    is_video: bool
    taken_at: str


@dataclass
class MediaResult:
    paths: list[Path]
    caption: str
    media_type: str


class InstagramService:
    def __init__(self) -> None:
        self._client: Client | None = None
        self._logged_in = False

    @property
    def is_ready(self) -> bool:
        return self._logged_in and self._client is not None

    def connect(self) -> bool:
        if not settings.instagram_username or not settings.instagram_password:
            logger.warning("Instagram credentials not configured")
            return False

        client = Client()
        session_path = settings.session_file
        session_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if session_path.exists():
                client.load_settings(session_path)
                client.login(
                    settings.instagram_username,
                    settings.instagram_password,
                )
                client.get_timeline_feed()
            else:
                client.login(
                    settings.instagram_username,
                    settings.instagram_password,
                )
                client.dump_settings(session_path)
            self._client = client
            self._logged_in = True
            logger.info("Instagram session ready for @%s", settings.instagram_username)
            return True
        except Exception:
            logger.exception("Instagram login failed")
            self._client = None
            self._logged_in = False
            return False

    def _require_client(self) -> Client:
        if not self._client or not self._logged_in:
            raise LoginRequired("Instagram not connected")
        return self._client

    def get_profile(self, username: str) -> ProfileResult:
        client = self._require_client()
        try:
            user_id = client.user_id_from_username(username)
            info = client.user_info(user_id)
        except UserNotFound as exc:
            raise ValueError("کاربر پیدا نشد / User not found") from exc
        except PrivateError as exc:
            raise ValueError("اکانت پرایوت است / Private account") from exc

        pic_url = str(info.profile_pic_url_hd or info.profile_pic_url)
        downloaded = client.photo_download_by_url(
            pic_url,
            folder="/tmp",
            filename=f"{username}_profile",
        )
        actual = Path(downloaded)
        if not actual.exists():
            candidates = sorted(
                Path("/tmp").glob(f"{username}_profile*"),
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
        )

    def get_stories(self, username: str) -> list[StoryItem]:
        client = self._require_client()
        try:
            user_id = client.user_id_from_username(username)
            stories = client.user_stories(user_id)
        except UserNotFound as exc:
            raise ValueError("کاربر پیدا نشد / User not found") from exc
        except PrivateError as exc:
            raise ValueError("اکانت پرایوت است / Private account") from exc

        if not stories:
            return []

        items: list[StoryItem] = []
        for story in stories:
            try:
                if story.media_type == 2:  # video
                    path = client.story_download(story.pk, folder="/tmp")
                    is_video = True
                else:
                    path = client.story_download(story.pk, folder="/tmp")
                    is_video = False
                taken = (
                    story.taken_at.strftime("%Y-%m-%d %H:%M")
                    if story.taken_at
                    else ""
                )
                items.append(StoryItem(path=Path(path), is_video=is_video, taken_at=taken))
            except ClientError:
                logger.warning("Failed to download story %s", story.pk)
        return items

    def download_media_url(self, url: str) -> MediaResult:
        client = self._require_client()
        try:
            media_pk = client.media_pk_from_url(url)
            media = client.media_info(media_pk)
        except MediaNotFound as exc:
            raise ValueError("پست پیدا نشد / Media not found") from exc

        paths: list[Path] = []
        caption = media.caption_text or ""

        if media.media_type == 8:  # album
            album_files = client.album_download(media_pk, folder="/tmp")
            paths = [Path(p) for p in album_files]
        else:
            paths.extend(self._download_media_item(client, media))

        if not paths:
            raise ValueError("فایلی برای دانلود نیست / Nothing to download")

        type_names = {1: "photo", 2: "video", 8: "album"}
        return MediaResult(
            paths=paths,
            caption=caption,
            media_type=type_names.get(media.media_type, "media"),
        )

    def _download_media_item(self, client: Client, media: Any) -> list[Path]:
        paths: list[Path] = []
        if media.media_type == 2:
            path = client.video_download(media.pk, folder="/tmp")
            paths.append(Path(path))
        elif media.media_type == 1:
            path = client.photo_download(media.pk, folder="/tmp")
            paths.append(Path(path))
        return paths


instagram_service = InstagramService()
