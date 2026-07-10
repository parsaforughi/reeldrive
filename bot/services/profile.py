"""Profile lookup: Apify first (no IG session needed), instagrapi fallback."""

import asyncio
import logging
from pathlib import Path

from bot.services.apify import apify_downloader
from bot.services.cdn_download import download_cdn_files
from bot.services.instagram import ProfileResult, instagram_downloader

logger = logging.getLogger(__name__)

_NO_PIC = Path("/tmp/reeldrive/__no_profile_pic__")

_NAME_KEYS = ("fullName", "full_name", "name")
_FOLLOWERS_KEYS = ("followersCount", "followerCount", "followers")
_FOLLOWING_KEYS = ("followsCount", "followingCount", "following")
_POSTS_KEYS = ("postsCount", "mediaCount", "posts")
_PIC_KEYS = ("profilePicUrlHD", "profilePicUrl", "profilePicture", "avatarUrl")
_PRIVATE_KEYS = ("private", "isPrivate")
_VERIFIED_KEYS = ("verified", "isVerified")


def _first_str(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        val = item.get(key)
        if val:
            return str(val)
    return ""


def _first_int(item: dict, keys: tuple[str, ...]) -> int:
    for key in keys:
        val = item.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    return 0


async def _fetch_via_apify(username: str) -> ProfileResult:
    item = await apify_downloader.fetch_profile_item(username)

    pic_url = _first_str(item, _PIC_KEYS)
    paths = await download_cdn_files([(pic_url, False)]) if pic_url else []

    return ProfileResult(
        username=_first_str(item, ("username",)) or username,
        full_name=_first_str(item, _NAME_KEYS),
        biography=apify_downloader.profile_biography(item),
        follower_count=_first_int(item, _FOLLOWERS_KEYS),
        following_count=_first_int(item, _FOLLOWING_KEYS),
        media_count=_first_int(item, _POSTS_KEYS),
        is_private=any(bool(item.get(k)) for k in _PRIVATE_KEYS),
        is_verified=any(bool(item.get(k)) for k in _VERIFIED_KEYS),
        profile_pic_path=paths[0] if paths else _NO_PIC,
        direct_urls=[pic_url] if pic_url else [],
    )


async def fetch_profile(username: str) -> ProfileResult:
    if apify_downloader.ready:
        try:
            return await _fetch_via_apify(username)
        except Exception:
            logger.warning(
                "Apify profile fetch failed for @%s, falling back to instagrapi",
                username,
                exc_info=True,
            )

    return await asyncio.to_thread(instagram_downloader.get_profile, username)
