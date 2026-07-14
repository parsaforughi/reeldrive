"""Following-list lookup: HikerAPI only.

Deliberately does not fall back to instagrapi — that would run through the
shared bridge Instagram session used for DM forwarding and other features,
risking a rate-limit/challenge on that account. If HikerAPI isn't configured
or fails, the lookup fails outright instead.
"""

import logging

from bot.config import settings
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
    if not hiker_client.ready:
        raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

    limit = limit or settings.max_following_list
    try:
        items = await hiker_client.fetch_following(username, limit)
    except ValueError:
        raise
    except Exception as exc:
        logger.warning("HikerAPI following fetch failed for @%s", username, exc_info=True)
        raise ValueError("خطای دریافت فالووینگ / Following fetch failed") from exc

    logger.info("HikerAPI following for @%s: %d raw item(s)", username, len(items))
    users = [u for item in items if (u := _parse_item(item))]
    if items and not users:
        logger.warning(
            "HikerAPI following for @%s: 0/%d items parsed — unexpected item shape, first item keys: %s",
            username,
            len(items),
            sorted(items[0].keys()) if isinstance(items[0], dict) else type(items[0]),
        )
    users.sort(key=lambda u: u.username)
    return users
