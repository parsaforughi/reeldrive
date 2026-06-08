"""Pro subscription helpers (Telegram Stars + admin dashboard)."""

from datetime import datetime, timedelta

from bot.db.engine import async_session
from bot.db.models import BotUser
from bot.time_utils import utc_now


def is_plan_active(user: BotUser | None) -> bool:
    if not user or user.subscription_plan == "free":
        return False
    exp = user.subscription_expires_at
    if exp is None:
        return user.subscription_plan in ("pro", "premium")
    return exp > utc_now()


def _parse_csv_lower(raw: str) -> frozenset[str]:
    return frozenset(x.strip().lower().lstrip("@") for x in raw.split(",") if x.strip())


def _parse_csv_ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return frozenset(out)


async def is_ai_unlimited(telegram_id: int, username: str | None = None) -> bool:
    """Owner/VIP — skip Pro gate and monthly AI limits."""
    from bot.config import settings

    if telegram_id in _parse_csv_ids(settings.ai_unlimited_telegram_ids):
        return True

    allowed = _parse_csv_lower(settings.ai_unlimited_usernames)
    if not allowed:
        return False

    if username and username.lower().lstrip("@") in allowed:
        return True

    user = await get_bot_user(telegram_id)
    if user and user.username and user.username.lower() in allowed:
        return True
    return False


async def has_pro_access(telegram_id: int, username: str | None = None) -> bool:
    if await is_ai_unlimited(telegram_id, username):
        return True
    user = await get_bot_user(telegram_id)
    return bool(
        is_plan_active(user) and user and user.subscription_plan in ("pro", "premium")
    )


async def get_bot_user(telegram_id: int) -> BotUser | None:
    async with async_session() as session:
        return await session.get(BotUser, telegram_id)


async def grant_pro(
    telegram_id: int,
    *,
    days: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> datetime:
    now = utc_now()
    async with async_session() as session:
        user = await session.get(BotUser, telegram_id)
        if not user:
            user = BotUser(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language="",
            )
            session.add(user)
        else:
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name

        base = now
        if (
            user.subscription_expires_at
            and user.subscription_expires_at > now
            and user.subscription_plan in ("pro", "premium")
        ):
            base = user.subscription_expires_at

        expires = base + timedelta(days=days)
        user.subscription_plan = "pro"
        user.subscription_expires_at = expires
        await session.commit()
        return expires
