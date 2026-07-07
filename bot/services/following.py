"""Following-list lookup: Apify first (no IG session needed), instagrapi fallback."""

import asyncio
import logging

from bot.config import settings
from bot.services.apify import apify_downloader
from bot.services.instagram import FollowUser, instagram_downloader

logger = logging.getLogger(__name__)

_USERNAME_KEYS = ("username", "handle", "login", "user_name")
_NAME_KEYS = ("full_name", "fullName", "name", "displayName", "introduction")
_PRIVATE_KEYS = ("is_private", "isPrivate", "private")
_VERIFIED_KEYS = ("is_verified", "isVerified", "verified")


def _first(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        val = item.get(key)
        if val:
            return str(val)
    return ""


def _parse_item(item: dict) -> FollowUser | None:
    username = _first(item, _USERNAME_KEYS).lstrip("@").lower()
    if not username:
        return None
    full_name = _first(item, _NAME_KEYS)
    is_private = any(bool(item.get(k)) for k in _PRIVATE_KEYS)
    is_verified = any(bool(item.get(k)) for k in _VERIFIED_KEYS)
    return FollowUser(
        username=username,
        full_name=full_name,
        is_private=is_private,
        is_verified=is_verified,
    )


async def _fetch_via_apify(username: str, limit: int) -> list[FollowUser]:
    items = await apify_downloader.fetch_following(username, limit)
    users = [u for item in items if (u := _parse_item(item))]
    users.sort(key=lambda u: u.username)
    return users


async def fetch_following(username: str, limit: int | None = None) -> list[FollowUser]:
    limit = limit or settings.max_following_list

    if apify_downloader.ready:
        try:
            return await _fetch_via_apify(username, limit)
        except Exception:
            logger.warning(
                "Apify following fetch failed for @%s, falling back to instagrapi",
                username,
                exc_info=True,
            )

    return await asyncio.to_thread(instagram_downloader.get_following, username, limit)
