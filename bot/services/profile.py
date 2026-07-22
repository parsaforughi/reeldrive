"""Instagram profile lookup through HikerAPI."""

import logging
from pathlib import Path

from bot.services.cdn_download import download_cdn_files
from bot.services.hikerapi import hiker_client
from bot.services.instagram import ProfileResult

logger = logging.getLogger(__name__)

_NO_PIC = Path("/tmp/reeldrive/__no_profile_pic__")

_NAME_KEYS = ("fullName", "full_name", "name")
_FOLLOWERS_KEYS = ("followersCount", "followerCount", "follower_count", "followers")
_FOLLOWING_KEYS = ("followsCount", "followingCount", "following_count", "following")
_POSTS_KEYS = ("postsCount", "mediaCount", "media_count", "posts")
_PIC_KEYS = (
    "profilePicUrlHD",
    "profilePicUrl",
    "profile_pic_url_hd",
    "profile_pic_url",
    "profilePicture",
    "avatarUrl",
)
_BIO_KEYS = ("biography", "bio")
_PRIVATE_KEYS = ("private", "isPrivate", "is_private")
_VERIFIED_KEYS = ("verified", "isVerified", "is_verified")


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


async def _fetch_via_hiker(username: str) -> ProfileResult:
    user = await hiker_client.fetch_profile(username)

    pic_url = _first_str(user, _PIC_KEYS)
    paths = await download_cdn_files([(pic_url, False)]) if pic_url else []

    return ProfileResult(
        username=_first_str(user, ("username",)) or username,
        full_name=_first_str(user, _NAME_KEYS),
        biography=_first_str(user, _BIO_KEYS),
        follower_count=_first_int(user, _FOLLOWERS_KEYS),
        following_count=_first_int(user, _FOLLOWING_KEYS),
        media_count=_first_int(user, _POSTS_KEYS),
        is_private=any(bool(user.get(k)) for k in _PRIVATE_KEYS),
        is_verified=any(bool(user.get(k)) for k in _VERIFIED_KEYS),
        profile_pic_path=paths[0] if paths else _NO_PIC,
        direct_urls=[pic_url] if pic_url else [],
    )


async def fetch_following_count(username: str) -> int:
    """Cheap follows-count lookup used before fetching the full list."""
    if not hiker_client.ready:
        raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")
    return await hiker_client.fetch_following_count(username)


async def fetch_profile(username: str) -> ProfileResult:
    if not hiker_client.ready:
        raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")
    return await _fetch_via_hiker(username)
