"""Following-list lookup.

Public targets use HikerAPI and its shared cache. Private targets may fall
back only to the requesting user's encrypted advanced session; private data
is deliberately never stored in the shared cache.
"""

import asyncio
import logging
import time

from bot.config import settings
from bot.services.hikerapi import HikerPrivateAccountError, hiker_client
from bot.services.instagram import FollowUser

logger = logging.getLogger(__name__)

_USERNAME_KEYS = ("username", "handle", "login", "user_name")
_NAME_KEYS = ("full_name", "fullName", "name", "displayName", "introduction")
_PRIVATE_KEYS = ("is_private", "isPrivate", "private")
_VERIFIED_KEYS = ("is_verified", "isVerified", "verified")

_cache: dict[tuple[str, int], tuple[float, tuple[FollowUser, ...]]] = {}
_inflight: dict[tuple[str, int], asyncio.Task[list[FollowUser]]] = {}


def following_ready() -> bool:
    return hiker_client.ready


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


def _cache_get(key: tuple[str, int]) -> list[FollowUser] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, users = entry
    if expires_at <= time.monotonic():
        _cache.pop(key, None)
        return None
    return list(users)


def _cache_put(key: tuple[str, int], users: list[FollowUser]) -> None:
    if not users or settings.following_cache_ttl_seconds <= 0:
        return
    max_entries = max(1, settings.following_cache_max_entries)
    max_users = max(1, settings.following_cache_max_users)
    if len(users) > max_users:
        return
    cached_users = sum(len(entry[1]) for entry in _cache.values())
    while _cache and (
        len(_cache) >= max_entries or cached_users + len(users) > max_users
    ):
        oldest = next(iter(_cache))
        removed = _cache.pop(oldest, None)
        if removed:
            cached_users -= len(removed[1])
    _cache[key] = (
        time.monotonic() + settings.following_cache_ttl_seconds,
        tuple(users),
    )


async def _fetch_and_cache(
    username: str, limit: int, key: tuple[str, int]
) -> list[FollowUser]:
    if not hiker_client.ready:
        raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")
    items = await hiker_client.fetch_following(username, limit)

    logger.info(
        "HikerAPI following for @%s: %d raw item(s)", username, len(items)
    )
    users = [u for item in items if (u := _parse_item(item))]
    if items and not users:
        logger.warning(
            "HikerAPI following for @%s: 0/%d items parsed — unexpected item shape, first item keys: %s",
            username,
            len(items),
            sorted(items[0].keys()) if isinstance(items[0], dict) else type(items[0]),
        )
    users.sort(key=lambda u: u.username)
    _cache_put(key, users)
    return users


def _parse_users(items: list[dict]) -> list[FollowUser]:
    users = [u for item in items if (u := _parse_item(item))]
    users.sort(key=lambda u: u.username)
    return users


async def fetch_following_count(
    username: str, telegram_id: int | None = None
) -> int:
    handle = hiker_client.normalize_username(username)
    profile = await hiker_client.fetch_profile(handle)
    is_private = any(bool(profile.get(key)) for key in _PRIVATE_KEYS)
    if is_private:
        if telegram_id is None:
            from bot.services.advanced_instagram import AdvancedConnectRequired

            raise AdvancedConnectRequired()
        from bot.services.advanced_instagram import advanced_instagram

        return await advanced_instagram.fetch_following_count(telegram_id, handle)

    for key in ("following_count", "followingCount", "follows_count"):
        value = profile.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


async def fetch_following(
    username: str,
    limit: int | None = None,
    *,
    telegram_id: int | None = None,
) -> list[FollowUser]:
    limit = limit or settings.max_following_list
    handle = hiker_client.normalize_username(username)
    key = (handle, limit)

    cached = _cache_get(key)
    if cached is not None:
        logger.info("Following cache hit for @%s (%d item(s))", handle, len(cached))
        return cached

    task = _inflight.get(key)
    if task is None:
        task = asyncio.create_task(_fetch_and_cache(handle, limit, key))
        _inflight[key] = task

        def clear_inflight(done: asyncio.Task[list[FollowUser]]) -> None:
            if _inflight.get(key) is done:
                _inflight.pop(key, None)

        task.add_done_callback(clear_inflight)
    try:
        return list(await asyncio.shield(task))
    except HikerPrivateAccountError:
        if telegram_id is None:
            from bot.services.advanced_instagram import AdvancedConnectRequired

            raise AdvancedConnectRequired()
        from bot.services.advanced_instagram import advanced_instagram

        items = await advanced_instagram.fetch_following(
            telegram_id, handle, limit
        )
        logger.info(
            "Advanced-session following telegram=%s target=@%s: %d raw item(s)",
            telegram_id,
            handle,
            len(items),
        )
        # Never put viewer-authorized private data in the process-wide cache.
        return _parse_users(items)
