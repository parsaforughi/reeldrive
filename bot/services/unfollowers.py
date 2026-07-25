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
    # False when the follower list was too large to fetch completely, so the
    # non-mutual result is a best-effort approximation over the scanned slice
    # (and the "fans" list is omitted because it can't be trusted).
    followers_complete: bool = True


def followers_scan_limit() -> int:
    """How many followers we are willing to scan for one report.

    We never pull an unbounded follower list: reciprocity for the *following*
    set (the bounded candidate set) is all we need, and the scan is capped so
    a mega-follower page can't run up the token bill or the request count.
    """
    return max(1, settings.max_following_list)


def token_cost_units(following_count: int, follower_count: int) -> int:
    """Accounts actually scraped from HikerAPI — the basis for pricing.

    The follower side is capped at ``followers_scan_limit()`` so a huge page
    is charged for what we scan, not its full (unfetched) follower count.
    """
    return following_count + min(follower_count, followers_scan_limit())


def _diff(a: list[FollowUser], b: list[FollowUser]) -> list[FollowUser]:
    """Users in ``a`` whose username is not present in ``b``."""
    b_names = {u.username for u in b}
    return [u for u in a if u.username not in b_names]


async def _fetch_sets(
    telegram_id: int,
    handle: str,
    *,
    follower_count: int,
    is_private: bool,
    limit: int,
) -> tuple[list[FollowUser], list[FollowUser], bool]:
    """Return (following, followers, followers_complete).

    Fetches the following list first (bounded, cheap). The follower list is
    only fetched when it can matter, and is skipped entirely when the page has
    no followers. Private pages fall back to the user's own advanced session.
    """
    from bot.services.advanced_instagram import (
        AdvancedConnectRequired,
        advanced_instagram,
    )

    async def via_session() -> tuple[list[FollowUser], list[FollowUser], bool]:
        if not await advanced_instagram.has_session(telegram_id):
            raise UnfollowerAccessRequired() from None
        try:
            f_items, fl_items = await advanced_instagram.fetch_own_follow_sets(
                telegram_id, limit
            )
        except AdvancedConnectRequired:
            raise UnfollowerAccessRequired() from None
        complete = follower_count <= limit
        return _parse_users(f_items), _parse_users(fl_items), complete

    if is_private:
        return await via_session()

    try:
        following = _parse_users(await hiker_client.fetch_following(handle, limit))
        if follower_count <= 0:
            # No followers at all → everyone you follow is a non-follower.
            return following, [], True
        followers = _parse_users(await hiker_client.fetch_followers(handle, limit))
    except HikerPrivateAccountError:
        return await via_session()

    # The follower list is complete only if the reported count fits within the
    # scan cap and we actually fetched (about) that many.
    complete = follower_count <= limit and len(followers) >= min(follower_count, limit)
    return following, followers, complete


async def build_report(
    telegram_id: int,
    username: str,
    *,
    following_count: int,
    follower_count: int,
    is_private: bool,
) -> UnfollowerReport:
    """Build the non-mutual report for ``username`` (the user's own page).

    ``following_count``/``follower_count``/``is_private`` come from the cheap
    ``precheck_counts`` call already made for pricing, so no extra profile
    request is spent here.
    """
    limit = followers_scan_limit()
    handle = hiker_client.normalize_username(username)

    following, followers, complete = await _fetch_sets(
        telegram_id,
        handle,
        follower_count=follower_count,
        is_private=is_private,
        limit=limit,
    )

    mutual = len({u.username for u in following} & {u.username for u in followers})
    logger.info(
        "Unfollower report @%s: following=%d followers=%d mutual=%d complete=%s",
        handle,
        len(following),
        len(followers),
        mutual,
        complete,
    )
    return UnfollowerReport(
        username=handle,
        following_count=len(following),
        followers_count=follower_count,
        mutual_count=mutual,
        not_following_back=_diff(following, followers),
        # A "fan" (follows you, you don't follow back) can only be asserted
        # against a COMPLETE follower list — omit it when the scan was capped.
        fans=_diff(followers, following) if complete else [],
        followers_complete=complete,
    )
