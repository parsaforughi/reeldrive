"""Admin-only commands."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.i18n import tu
from bot.services.following_access import grant_credits, is_admin

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("addtokens"))
async def cmd_add_tokens(message: Message) -> None:
    uid = message.from_user.id
    if not is_admin(uid):
        return

    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(
            "فرمت درست:\n<code>/addtokens telegram_id count</code>\n"
            "مثال: <code>/addtokens 99686187 5</code>"
        )
        return

    _, tg_raw, count_raw = parts
    try:
        target_id = int(tg_raw)
        count = int(count_raw)
    except ValueError:
        await message.answer("آیدی تلگرام و تعداد باید عدد باشند.")
        return

    if count < 1:
        await message.answer("تعداد باید حداقل ۱ باشد.")
        return

    balance = await grant_credits(target_id, count, granted_by=uid)
    await message.answer(
        f"✅ {count} توکن برای کاربر {target_id} فعال شد (موجودی فعلی: {balance})."
    )

    try:
        await message.bot.send_message(
            target_id,
            await tu(
                target_id,
                "following_tokens_granted_notify",
                count=count,
                balance=balance,
            ),
        )
    except Exception:
        logger.warning(
            "Could not notify user %s about %s granted tokens",
            target_id,
            count,
            exc_info=True,
        )
