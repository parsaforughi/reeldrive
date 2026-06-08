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
