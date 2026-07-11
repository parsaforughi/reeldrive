"""Access control for the following-list feature:

1. User must currently be a member of every channel in
   ``settings.following_required_channels`` (checked live via the Bot API —
   leaving a channel revokes access on the next check, nothing is cached).
2. Each distinct target account ("page") the user looks up must be unlocked.
   The first ``settings.following_free_pages`` accounts are free once the
   channels are joined; every account after that consumes one paid token.
   Tokens are bought in whatever quantity the user picks, via a manual
   card-to-card payment (rotated across ``settings.following_support_cards``
   every ``settings.following_cards_rotate_every`` confirmed purchases), and
   credited by an admin via /addtokens.
"""

import logging

from aiogram import Bot
from sqlalchemy import func, select

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import FollowingCredit, FollowingCreditGrant, FollowingUnlock

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


def admin_ids() -> frozenset[int]:
    return _parse_csv_ids(settings.admin_telegram_ids)


def is_admin(telegram_id: int) -> bool:
    return telegram_id in admin_ids()


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


def free_page_count() -> int:
    return max(0, settings.following_free_pages)


def support_cards() -> list[str]:
    return [
        c.strip()
        for c in (settings.following_support_cards or "").split(",")
        if c.strip()
    ]


def payment_surcharge(telegram_id: int) -> int:
    """Small per-user amount added on top of the base price so support can
    tell buyers apart by the exact figure that lands in the bank account."""
    return 1 + (telegram_id % 300)


def token_price(count: int, telegram_id: int) -> int:
    return count * settings.following_page_price_toman + payment_surcharge(telegram_id)


async def total_credit_grants() -> int:
    async with async_session() as session:
        return (
            await session.scalar(select(func.count()).select_from(FollowingCreditGrant))
            or 0
        )


async def current_support_card() -> str:
    cards = support_cards()
    if not cards:
        return ""
    n = await total_credit_grants()
    idx = (n // max(1, settings.following_cards_rotate_every)) % len(cards)
    return cards[idx]


async def is_unlocked(telegram_id: int, target_username: str) -> bool:
    async with async_session() as session:
        existing = await session.scalar(
            select(FollowingUnlock.id).where(
                FollowingUnlock.telegram_id == telegram_id,
                FollowingUnlock.target_username == target_username,
            )
        )
    return existing is not None


async def unlocked_count(telegram_id: int) -> int:
    async with async_session() as session:
        return (
            await session.scalar(
                select(func.count())
                .select_from(FollowingUnlock)
                .where(FollowingUnlock.telegram_id == telegram_id)
            )
            or 0
        )


async def get_credit_balance(telegram_id: int) -> int:
    async with async_session() as session:
        balance = await session.scalar(
            select(FollowingCredit.balance).where(
                FollowingCredit.telegram_id == telegram_id
            )
        )
    return balance or 0


async def _unlock_account(
    telegram_id: int, target_username: str, *, granted_by: int | None = None
) -> None:
    async with async_session() as session:
        session.add(
            FollowingUnlock(
                telegram_id=telegram_id,
                target_username=target_username,
                page_number=1,
                granted_by=granted_by,
            )
        )
        await session.commit()


async def _consume_credit(telegram_id: int) -> bool:
    async with async_session() as session:
        credit = await session.get(FollowingCredit, telegram_id)
        if not credit or credit.balance < 1:
            return False
        credit.balance -= 1
        await session.commit()
        return True


async def has_access(telegram_id: int, target_username: str) -> bool:
    """Read-only check — would granting access succeed (already unlocked,
    free quota, or a token to spend)? Call this BEFORE the (paid) Apify
    fetch, so users with no tokens never trigger an actual scrape."""
    if await is_unlocked(telegram_id, target_username):
        return True
    if await unlocked_count(telegram_id) < free_page_count():
        return True
    return await get_credit_balance(telegram_id) > 0


async def grant_access(telegram_id: int, target_username: str) -> bool:
    """Actually unlocks + spends a token if needed. Call only after a
    successful, non-empty fetch, so a failed/empty lookup never costs a
    token even if ``has_access`` said yes."""
    if await is_unlocked(telegram_id, target_username):
        return True

    if await unlocked_count(telegram_id) < free_page_count():
        await _unlock_account(telegram_id, target_username)
        return True

    if await _consume_credit(telegram_id):
        await _unlock_account(telegram_id, target_username)
        return True

    return False


async def grant_credits(
    telegram_id: int, tokens: int, *, granted_by: int | None = None
) -> int:
    """Adds tokens to the user's balance and logs the grant (which also
    drives support-card rotation). Returns the new balance."""
    async with async_session() as session:
        credit = await session.get(FollowingCredit, telegram_id)
        if credit is None:
            credit = FollowingCredit(telegram_id=telegram_id, balance=0)
            session.add(credit)
        credit.balance += tokens
        session.add(
            FollowingCreditGrant(telegram_id=telegram_id, tokens=tokens, granted_by=granted_by)
        )
        await session.commit()
        return credit.balance
