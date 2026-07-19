"""Following-list lookup: HikerAPI first, with Apify fallback.

Deliberately does not fall back to instagrapi — that would run through the
shared bridge Instagram session used for DM forwarding and other features,
risking a rate-limit/challenge on that account.
"""

import logging

from bot.config import settings
from bot.services.apify import apify_downloader
from bot.services.hikerapi import hiker_client
from bot.services.instagram import FollowUser

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


async def fetch_following(username: str, limit: int | None = None) -> list[FollowUser]:
    limit = limit or settings.max_following_list
    items: list[dict] = []
    provider = ""
    hiker_error: Exception | None = None

    if hiker_client.ready:
        try:
            items = await hiker_client.fetch_following(username, limit)
            provider = "HikerAPI"
        except Exception as exc:
            hiker_error = exc
            logger.warning(
                "HikerAPI following fetch failed for @%s; trying Apify fallback",
                username,
                exc_info=True,
            )

    if not provider and apify_downloader.ready:
        try:
            items = await apify_downloader.fetch_following(username, limit)
            provider = "Apify"
        except ValueError:
            raise
        except Exception as exc:
            logger.warning(
                "Apify following fetch failed for @%s", username, exc_info=True
            )
            raise ValueError(
                "خطای سرویس در دریافت فالووینگ / Following provider failed"
            ) from exc

    if not provider:
        if isinstance(hiker_error, ValueError):
            raise hiker_error
        raise ValueError("HikerAPI/Apify تنظیم نشده / provider not configured")

    logger.info(
        "%s following for @%s: %d raw item(s)",
        provider,
        username,
        len(items),
    )
    users = [u for item in items if (u := _parse_item(item))]
    if items and not users:
        logger.warning(
            "%s following for @%s: 0/%d items parsed — unexpected item shape, first item keys: %s",
            provider,
            username,
            len(items),
            sorted(items[0].keys()) if isinstance(items[0], dict) else type(items[0]),
        )
    users.sort(key=lambda u: u.username)
    return users
