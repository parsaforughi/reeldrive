"""Profile lookup: HikerAPI, then Apify, then instagrapi fallback."""

import asyncio
import logging
from pathlib import Path

from bot.services.apify import apify_downloader
from bot.services.cdn_download import download_cdn_files
from bot.services.hikerapi import hiker_client
from bot.services.instagram import ProfileResult, instagram_downloader

logger = logging.getLogger(__name__)

_NO_PIC = Path("/tmp/reeldrive/__no_profile_pic__")

_NAME_KEYS = ("fullName", "full_name", "name")
_FOLLOWERS_KEYS = (
    "followersCount",
    "followerCount",
    "follower_count",
    "followers",
)
_FOLLOWING_KEYS = (
    "followsCount",
    "followingCount",
    "following_count",
    "following",
)
_POSTS_KEYS = ("postsCount", "mediaCount", "media_count", "posts")
_PIC_KEYS = (
    "profilePicUrlHD",
    "profilePicUrl",
    "profile_pic_url_hd",
    "profile_pic_url",
    "profilePicture",
    "avatarUrl",
)
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


async def _profile_result(
    item: dict, username: str, *, biography: str
) -> ProfileResult:
    pic_url = _first_str(item, _PIC_KEYS)
    paths = await download_cdn_files([(pic_url, False)]) if pic_url else []

    return ProfileResult(
        username=_first_str(item, ("username",)) or username,
        full_name=_first_str(item, _NAME_KEYS),
        biography=biography,
        follower_count=_first_int(item, _FOLLOWERS_KEYS),
        following_count=_first_int(item, _FOLLOWING_KEYS),
        media_count=_first_int(item, _POSTS_KEYS),
        is_private=any(bool(item.get(k)) for k in _PRIVATE_KEYS),
        is_verified=any(bool(item.get(k)) for k in _VERIFIED_KEYS),
        profile_pic_path=paths[0] if paths else _NO_PIC,
        direct_urls=[pic_url] if pic_url else [],
    )


async def _fetch_via_hiker(username: str) -> ProfileResult:
    item = await hiker_client.fetch_profile_item(username)
    return await _profile_result(
        item,
        username,
        biography=hiker_client.profile_biography(item),
    )


async def _fetch_via_apify(username: str) -> ProfileResult:
    item = await apify_downloader.fetch_profile_item(username)
    return await _profile_result(
        item,
        username,
        biography=apify_downloader.profile_biography(item),
    )


async def fetch_profile(username: str) -> ProfileResult:
    if hiker_client.ready:
        try:
            return await _fetch_via_hiker(username)
        except Exception:
            logger.warning(
                "HikerAPI profile fetch failed for @%s, trying fallback",
                username,
                exc_info=True,
            )

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
