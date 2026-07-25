"""Unfollower / non-mutual analysis for the user's own connected page.

"آنفالویاب" — compares the connected account's following list against its
followers list and reports:

  * not_following_back — accounts you follow that do NOT follow you back
  * fans              — accounts that follow you but you do NOT follow back
  * mutual_count      — how many are mutual

Public pages are read from HikerAPI. A private page (or a HikerAPI private
error) falls back to the requesting user's own encrypted advanced session,
which can always read its own follow graph. Nothing private is cached.
"""

import asyncio
import logging
from dataclasses import dataclass, field

from bot.config import settings
from bot.services.following import _parse_users
from bot.services.hikerapi import HikerPrivateAccountError, hiker_client
from bot.services.instagram import FollowUser

logger = logging.getLogger(__name__)


class UnfollowerAccessRequired(ValueError):
    """The page is private and the user has no advanced session to read it."""


_FOLLOWING_COUNT_KEYS = ("following_count", "followingCount", "follows_count")
_FOLLOWER_COUNT_KEYS = (
    "follower_count",
    "followerCount",
    "followed_by_count",
    "followers_count",
    "edge_followed_by",
)
_PRIVATE_KEYS = ("is_private", "isPrivate", "private")


def _int_from(profile: dict, keys: tuple[str, ...]) -> int:
    for key in keys:
        value = profile.get(key)
        if isinstance(value, dict):  # e.g. {"count": N}
            value = value.get("count")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


async def precheck_counts(username: str) -> tuple[int, int, bool]:
    """Cheap single profile call → (following_count, follower_count, is_private).

    Follower/following counts are public even for a private account, so this
    is enough to price the lookup *before* the expensive follow-graph scrape.
    """
    profile = await hiker_client.fetch_profile(username)
    following = _int_from(profile, _FOLLOWING_COUNT_KEYS)
    followers = _int_from(profile, _FOLLOWER_COUNT_KEYS)
    is_private = any(bool(profile.get(key)) for key in _PRIVATE_KEYS)
    return following, followers, is_private


@dataclass
class UnfollowerReport:
    username: str
    following_count: int
    followers_count: int
    mutual_count: int
    not_following_back: list[FollowUser] = field(default_factory=list)
    fans: list[FollowUser] = field(default_factory=list)


def _diff(a: list[FollowUser], b: list[FollowUser]) -> list[FollowUser]:
    """Users in ``a`` whose username is not present in ``b``."""
    b_names = {u.username for u in b}
    return [u for u in a if u.username not in b_names]


async def _fetch_public(username: str, limit: int) -> tuple[list[FollowUser], list[FollowUser]]:
    following_items, follower_items = await asyncio.gather(
        hiker_client.fetch_following(username, limit),
        hiker_client.fetch_followers(username, limit),
    )
    return _parse_users(following_items), _parse_users(follower_items)


async def build_report(telegram_id: int, username: str) -> UnfollowerReport:
    """Build the non-mutual report for ``username`` (the user's own page)."""
    limit = settings.max_following_list
    handle = hiker_client.normalize_username(username)

    try:
        following, followers = await _fetch_public(handle, limit)
    except HikerPrivateAccountError:
        from bot.services.advanced_instagram import (
            AdvancedConnectRequired,
            advanced_instagram,
        )

        if not await advanced_instagram.has_session(telegram_id):
            raise UnfollowerAccessRequired() from None
        try:
            following_items, follower_items = (
                await advanced_instagram.fetch_own_follow_sets(telegram_id, limit)
            )
        except AdvancedConnectRequired:
            raise UnfollowerAccessRequired() from None
        following = _parse_users(following_items)
        followers = _parse_users(follower_items)

    mutual = len({u.username for u in following} & {u.username for u in followers})
    logger.info(
        "Unfollower report @%s: following=%d followers=%d mutual=%d",
        handle,
        len(following),
        len(followers),
        mutual,
    )
    return UnfollowerReport(
        username=handle,
        following_count=len(following),
        followers_count=len(followers),
        mutual_count=mutual,
        not_following_back=_diff(following, followers),
        fans=_diff(followers, following),
    )
