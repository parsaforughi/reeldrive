"""Access control for the following-list feature:

1. User must currently be a member of every channel in
   ``settings.following_required_channels`` PLUS one channel from
   ``settings.following_alternate_channels`` (alternated per user, see
   ``required_channels``) — checked live via the Bot API, so leaving a
   channel revokes access on the next check, nothing is cached.
2. Each distinct target account ("page") the user looks up must be unlocked.
   The first ``settings.following_free_pages`` accounts are free once the
   channels are joined; every account after that consumes
   ``tokens_required_for_count(following_count)`` paid tokens — one token
   per started batch of ``FOLLOWINGS_PER_TOKEN`` followings (e.g. an 800-
   following page costs 2 tokens). The count is looked up cheaply via the
   profile-details API call *before* the expensive followings-list fetch
   runs, so a user without enough tokens never triggers it.
   Tokens are bought in whatever quantity the user picks, via a manual
   card-to-card payment (rotated across ``settings.following_support_cards``
   every ``settings.following_cards_rotate_every`` confirmed purchases), and
   credited by an admin via /addtokens.
"""

import logging
import math

from aiogram import Bot
from sqlalchemy import func, select

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import FollowingCredit, FollowingCreditGrant, FollowingUnlock
from bot.services.app_settings import get_setting, set_setting

logger = logging.getLogger(__name__)

_JOINED_STATUSES = frozenset({"member", "administrator", "creator"})

FOLLOWINGS_PER_TOKEN = 400

# DB-setting keys for the admin-panel-editable payment card — overrides
# settings.following_support_cards / following_card_holder_name when set,
# so admins can change the card without an env var change + redeploy.
_CARD_NUMBER_KEY = "following_support_card"
_CARD_HOLDER_KEY = "following_card_holder_name"

# DB-setting keys for the admin-panel-editable join channels — overrides
# settings.following_required_channels / following_alternate_channels when
# set, so admins can swap a channel without an env var change + redeploy.
_REQUIRED_CHANNELS_KEY = "following_required_channels"
_ALTERNATE_CHANNELS_KEY = "following_alternate_channels"


def tokens_required_for_count(following_count: int) -> int:
    """Every started batch of FOLLOWINGS_PER_TOKEN followings costs one
    token (e.g. 800 followings -> 2 tokens, 450 -> 2 tokens)."""
    return max(1, math.ceil(following_count / FOLLOWINGS_PER_TOKEN))


def _split_csv(raw: str) -> list[str]:
    return [c.strip() for c in (raw or "").split(",") if c.strip()]


async def current_required_channels() -> str:
    override = await get_setting(_REQUIRED_CHANNELS_KEY)
    return override if override is not None else settings.following_required_channels


async def current_alternate_channels() -> str:
    override = await get_setting(_ALTERNATE_CHANNELS_KEY)
    return override if override is not None else settings.following_alternate_channels


async def set_channels(required: str, alternate: str) -> None:
    """Admin-panel override for the required/alternate join channels — takes
    effect immediately for every new membership check, no redeploy needed."""
    await set_setting(_REQUIRED_CHANNELS_KEY, required.strip())
    await set_setting(_ALTERNATE_CHANNELS_KEY, alternate.strip())


async def required_channels(telegram_id: int) -> list[str]:
    """Base channels are required for everyone. On top of those, each user
    must also join exactly one channel from the alternate channels —
    picked deterministically per telegram_id, alternating across users so
    the join load is split evenly instead of piling onto a single channel."""
    base = _split_csv(await current_required_channels())
    alternates = _split_csv(await current_alternate_channels())
    if alternates:
        base = base + [alternates[telegram_id % len(alternates)]]
    return base


def _parse_csv_ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return frozenset(out)


def admin_ids() -> frozenset[int]:
    return _parse_csv_ids(settings.admin_telegram_ids)


def notify_ids() -> frozenset[int]:
    """Who gets pushed receipt/purchase-request messages — falls back to
    all admins if unset."""
    ids = _parse_csv_ids(settings.following_notify_ids)
    return ids or admin_ids()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in admin_ids()


async def missing_channels(bot: Bot, telegram_id: int) -> list[str]:
    """Live-checks membership — never cached, so leaving a channel is picked
    up on the very next call."""
    missing: list[str] = []
    for channel in await required_channels(telegram_id):
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


def to_rial(toman: int) -> int:
    """Bank statements in Iran show Rial (1 Toman = 10 Rial) — convert at
    display time only; all pricing settings/logic stay in Toman."""
    return toman * 10


def token_price(count: int, telegram_id: int) -> int:
    return count * settings.following_page_price_toman + payment_surcharge(telegram_id)


async def total_credit_grants() -> int:
    async with async_session() as session:
        return (
            await session.scalar(select(func.count()).select_from(FollowingCreditGrant))
            or 0
        )


async def current_support_card() -> str:
    override = await get_setting(_CARD_NUMBER_KEY)
    if override:
        return override

    cards = support_cards()
    if not cards:
        return ""
    n = await total_credit_grants()
    idx = (n // max(1, settings.following_cards_rotate_every)) % len(cards)
    return cards[idx]


async def current_card_holder_name() -> str:
    return await get_setting(_CARD_HOLDER_KEY) or settings.following_card_holder_name


async def set_support_card(card: str, holder: str) -> None:
    """Admin-panel override for the payment card — takes effect immediately
    for every new purchase prompt, no redeploy needed."""
    await set_setting(_CARD_NUMBER_KEY, card.strip())
    await set_setting(_CARD_HOLDER_KEY, holder.strip())


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


async def _consume_credit(telegram_id: int, amount: int = 1) -> bool:
    async with async_session() as session:
        credit = await session.get(FollowingCredit, telegram_id)
        if not credit or credit.balance < amount:
            return False
        credit.balance -= amount
        await session.commit()
        return True


async def has_access(telegram_id: int, target_username: str, tokens_needed: int = 1) -> bool:
    """Read-only check — would granting access succeed (already unlocked,
    free quota, or enough tokens to spend)? Call this BEFORE the (paid,
    expensive) followings-list fetch, so users without enough tokens
    never trigger it. ``tokens_needed`` should come from
    ``tokens_required_for_count`` using a cheap prior follows-count lookup."""
    if await is_unlocked(telegram_id, target_username):
        return True
    if await unlocked_count(telegram_id) < free_page_count():
        return True
    return await get_credit_balance(telegram_id) >= tokens_needed


async def grant_access(telegram_id: int, target_username: str, tokens_needed: int = 1) -> bool:
    """Actually unlocks + spends ``tokens_needed`` tokens if not free. Call
    only after a successful, non-empty fetch, so a failed/empty lookup never
    costs tokens even if ``has_access`` said yes."""
    if await is_unlocked(telegram_id, target_username):
        return True

    if await unlocked_count(telegram_id) < free_page_count():
        await _unlock_account(telegram_id, target_username)
        return True

    if await _consume_credit(telegram_id, tokens_needed):
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
