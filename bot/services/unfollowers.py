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


async def precheck_counts(username: str) -> tuple[int, int, bool, str]:
    """Cheap single profile call → (following, follower, is_private, user_id).

    Follower/following counts are public even for a private account, so this
    is enough to price the lookup *before* the expensive follow-graph scrape.
    The user_id (pk) is returned so the search strategy needs no extra lookup.
    """
    profile = await hiker_client.fetch_profile(username)
    following = _int_from(profile, _FOLLOWING_COUNT_KEYS)
    followers = _int_from(profile, _FOLLOWER_COUNT_KEYS)
    is_private = any(bool(profile.get(key)) for key in _PRIVATE_KEYS)
    user_id = str(profile.get("pk") or profile.get("id") or "")
    return following, followers, is_private, user_id


@dataclass
class UnfollowerReport:
    username: str
    following_count: int
    followers_count: int
    mutual_count: int
    not_following_back: list[FollowUser] = field(default_factory=list)
    fans: list[FollowUser] = field(default_factory=list)
    # Is the "doesn't follow you back" list exact? True for the bulk path with
    # a complete follower list and for the search path; False only when a huge
    # private page had to be scanned partially.
    not_back_exact: bool = True
    # Whether the "fans" list (follows you, you don't follow back) was computed.
    # The search path can't produce it (it never enumerates the full followers).
    fans_available: bool = True


# Approx followers returned per bulk page. The per-candidate search wins only
# when the follower list dwarfs the following set by more than this factor.
_SEARCH_PAGE_SIZE = 50
# Above this following size, one-by-one search is itself too many requests, so
# we stay on the bulk path (and accept the follower-scan cap).
_SEARCH_MAX_FOLLOWING = 5000


def followers_scan_limit() -> int:
    """How many followers we are willing to bulk-scan for one report."""
    return max(1, settings.max_following_list)


def _choose_strategy(following_count: int, follower_count: int) -> tuple[str, int]:
    """Pick the cheaper *exact* strategy and return (name, token_cost_units).

    - "search": fetch the (small) following list, then test each account's
      reciprocity via /user/search/followers — ~following_count requests, and
      it never touches the giant follower list. Chosen when followers dwarf
      following (influencer/business pages).
    - "bulk": fetch both lists and diff — cheapest when the two are of similar
      size. The follower side is priced/capped at followers_scan_limit().
    """
    cap = followers_scan_limit()
    if (
        0 < following_count <= _SEARCH_MAX_FOLLOWING
        and follower_count > following_count * _SEARCH_PAGE_SIZE
    ):
        # list fetch (~following) + one search per following.
        return "search", following_count * 2
    return "bulk", following_count + min(follower_count, cap)


def token_cost_units(following_count: int, follower_count: int) -> int:
    """Pricing basis — the accounts/requests the chosen strategy will spend."""
    return _choose_strategy(following_count, follower_count)[1]


def _diff(a: list[FollowUser], b: list[FollowUser]) -> list[FollowUser]:
    """Users in ``a`` whose username is not present in ``b``."""
    b_names = {u.username for u in b}
    return [u for u in a if u.username not in b_names]


async def _fetch_via_session(
    telegram_id: int, follower_count: int, limit: int
) -> tuple[list[FollowUser], list[FollowUser], bool]:
    """Private own-page path: read both lists from the user's own session."""
    from bot.services.advanced_instagram import (
        AdvancedConnectRequired,
        advanced_instagram,
    )

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


async def build_report(
    telegram_id: int,
    username: str,
    *,
    following_count: int,
    follower_count: int,
    is_private: bool,
    user_id: str = "",
) -> UnfollowerReport:
    """Build the non-mutual report for ``username`` (the user's own page).

    Counts/privacy/user_id come from the cheap ``precheck_counts`` call already
    made for pricing, so no extra profile request is spent here.
    """
    limit = followers_scan_limit()
    handle = hiker_client.normalize_username(username)

    # --- Search strategy: exact, and never pulls the giant follower list. ---
    strategy, _ = _choose_strategy(following_count, follower_count)
    if strategy == "search" and not is_private and user_id:
        try:
            following = _parse_users(
                await hiker_client.fetch_following(handle, limit)
            )
            follow_back = await hiker_client.followers_follow_back(
                user_id, [u.username for u in following]
            )
        except HikerPrivateAccountError:
            following, followers, complete = await _fetch_via_session(
                telegram_id, follower_count, limit
            )
        else:
            not_back = [u for u in following if u.username not in follow_back]
            logger.info(
                "Unfollower report @%s [search]: following=%d follow_back=%d ghosts=%d",
                handle,
                len(following),
                len(follow_back),
                len(not_back),
            )
            return UnfollowerReport(
                username=handle,
                following_count=len(following),
                followers_count=follower_count,
                mutual_count=len(following) - len(not_back),
                not_following_back=not_back,
                fans=[],
                not_back_exact=True,
                fans_available=False,
            )
    else:
        # --- Bulk strategy: fetch both lists and diff. ---
        if is_private:
            following, followers, complete = await _fetch_via_session(
                telegram_id, follower_count, limit
            )
        else:
            try:
                following = _parse_users(
                    await hiker_client.fetch_following(handle, limit)
                )
                if follower_count <= 0:
                    followers, complete = [], True
                else:
                    followers = _parse_users(
                        await hiker_client.fetch_followers(handle, limit)
                    )
                    complete = follower_count <= limit and len(followers) >= min(
                        follower_count, limit
                    )
            except HikerPrivateAccountError:
                following, followers, complete = await _fetch_via_session(
                    telegram_id, follower_count, limit
                )

    mutual = len({u.username for u in following} & {u.username for u in followers})
    logger.info(
        "Unfollower report @%s [bulk]: following=%d followers=%d mutual=%d complete=%s",
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
        # A "fan" can only be asserted against a COMPLETE follower list.
        fans=_diff(followers, following) if complete else [],
        not_back_exact=complete,
        fans_available=complete,
    )
