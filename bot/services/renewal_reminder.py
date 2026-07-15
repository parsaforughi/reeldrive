"""Background loop: nudges Pro users ~2 days before their subscription expires."""

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot
from sqlalchemy import select

from bot.db.engine import async_session
from bot.db.models import BotUser
from bot.i18n import get_user_lang, tu
from bot.keyboards import subscription_shop_kb
from bot.time_utils import utc_now

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 6 * 3600
_REMINDER_WINDOW = timedelta(days=2)


class RenewalReminder:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._running = False

    async def run_loop(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Renewal reminder tick failed")
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        now = utc_now()
        window_end = now + _REMINDER_WINDOW

        async with async_session() as session:
            rows = (
                await session.execute(
                    select(BotUser).where(
                        BotUser.subscription_plan == "pro",
                        BotUser.subscription_expires_at.isnot(None),
                        BotUser.subscription_expires_at > now,
                        BotUser.subscription_expires_at <= window_end,
                    )
                )
            ).scalars().all()

            due = [u for u in rows if u.renewal_reminder_expiry != u.subscription_expires_at]
            targets = [(u.telegram_id, u.subscription_expires_at) for u in due]
            for u in due:
                u.renewal_reminder_expiry = u.subscription_expires_at
            await session.commit()

        for telegram_id, expires_at in targets:
            await self._notify(telegram_id, expires_at)

    async def _notify(self, telegram_id: int, expires_at) -> None:
        lang = await get_user_lang(telegram_id) or "fa"
        try:
            await self.bot.send_message(
                telegram_id,
                await tu(
                    telegram_id,
                    "pro_renewal_reminder",
                    date=expires_at.strftime("%Y-%m-%d"),
                ),
                reply_markup=subscription_shop_kb(lang),
            )
        except Exception:
            logger.warning(
                "Could not send renewal reminder to %s", telegram_id, exc_info=True
            )
