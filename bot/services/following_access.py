"""Access control for the following-list feature:

1. User must currently be a member of every channel in
   ``settings.following_required_channels`` (checked live via the Bot API —
   leaving a channel revokes access on the next check, nothing is cached).
2. The following-list is split into ``settings.following_page_count`` pages;
   each page must be individually unlocked. Unlocking happens out-of-band:
   the user sends a manual card-to-card payment to support (same flow used
   elsewhere in the bot), and an admin runs /grantpage to record the unlock.
"""

import logging

from aiogram import Bot
from sqlalchemy import select

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import FollowingUnlock
from bot.services.instagram import FollowUser

logger = logging.getLogger(__name__)

_JOINED_STATUSES = frozenset({"member", "administrator", "creator"})


def required_channels() -> list[str]:
    return [
        c.strip()
        for c in (settings.following_required_channels or "").split(",")
        if c.strip()
    ]


def _parse_csv_ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return frozenset(out)


def is_admin(telegram_id: int) -> bool:
    return telegram_id in _parse_csv_ids(settings.admin_telegram_ids)


async def missing_channels(bot: Bot, telegram_id: int) -> list[str]:
    """Live-checks membership — never cached, so leaving a channel is picked
    up on the very next call."""
    missing: list[str] = []
    for channel in required_channels():
        handle = "@" + channel.lstrip("@")
        try:
            member = await bot.get_chat_member(chat_id=handle, user_id=telegram_id)
            if member.status not in _JOINED_STATUSES:
                missing.append(channel)
        except Exception:
            logger.warning(
                "Could not verify membership of %s in %s", telegram_id, handle,
                exc_info=True,
            )
            missing.append(channel)
    return missing


def channel_url(channel: str) -> str:
    return f"https://t.me/{channel.lstrip('@')}"


def page_count() -> int:
    return max(1, settings.following_page_count)


def free_page_count() -> int:
    """First N pages are unlocked just by joining the required channels."""
    return max(0, min(settings.following_free_pages, page_count()))


def paginate(users: list[FollowUser]) -> list[list[FollowUser]]:
    n = page_count()
    total = len(users)
    base, rem = divmod(total, n)
    pages: list[list[FollowUser]] = []
    start = 0
    for i in range(n):
        size = base + (1 if i < rem else 0)
        pages.append(users[start : start + size])
        start += size
    return pages


async def is_page_unlocked(telegram_id: int, target_username: str, page_number: int) -> bool:
    if page_number <= free_page_count():
        return True
    async with async_session() as session:
        existing = await session.scalar(
            select(FollowingUnlock.id).where(
                FollowingUnlock.telegram_id == telegram_id,
                FollowingUnlock.target_username == target_username,
                FollowingUnlock.page_number == page_number,
            )
        )
    return existing is not None


async def unlocked_pages(telegram_id: int, target_username: str) -> set[int]:
    free = set(range(1, free_page_count() + 1))
    async with async_session() as session:
        rows = await session.scalars(
            select(FollowingUnlock.page_number).where(
                FollowingUnlock.telegram_id == telegram_id,
                FollowingUnlock.target_username == target_username,
            )
        )
    return free | set(rows.all())


async def unlock_page(
    telegram_id: int,
    target_username: str,
    page_number: int,
    *,
    granted_by: int | None = None,
) -> bool:
    """Returns True if this created a new unlock, False if it already existed."""
    if await is_page_unlocked(telegram_id, target_username, page_number):
        return False
    async with async_session() as session:
        session.add(
            FollowingUnlock(
                telegram_id=telegram_id,
                target_username=target_username,
                page_number=page_number,
                granted_by=granted_by,
            )
        )
        await session.commit()
    return True
