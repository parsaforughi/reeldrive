"""Admin-only commands."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.i18n import tu
from bot.services.following_access import is_admin, unlock_page

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("grantpage"))
async def cmd_grant_page(message: Message) -> None:
    uid = message.from_user.id
    if not is_admin(uid):
        return

    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.answer(
            "فرمت درست:\n<code>/grantpage telegram_id username page</code>\n"
            "مثال: <code>/grantpage 99686187 cristiano 2</code>"
        )
        return

    _, tg_raw, target_username, page_raw = parts
    try:
        target_id = int(tg_raw)
        page = int(page_raw)
    except ValueError:
        await message.answer("آیدی تلگرام و شماره صفحه باید عدد باشند.")
        return

    target_username = target_username.strip().lstrip("@").lower()
    if page < 1 or page > 10:
        await message.answer("شماره صفحه نامعتبر است.")
        return

    created = await unlock_page(target_id, target_username, page, granted_by=uid)
    if created:
        await message.answer(
            f"✅ صفحه {page} از فالووینگ @{target_username} برای کاربر {target_id} باز شد."
        )
    else:
        await message.answer("قبلاً برای این کاربر باز شده بود.")

    try:
        await message.bot.send_message(
            target_id,
            await tu(
                target_id,
                "following_page_unlocked_notify",
                page=page,
                username=target_username,
            ),
        )
    except Exception:
        logger.warning(
            "Could not notify user %s about unlocked page %s/%s",
            target_id,
            target_username,
            page,
            exc_info=True,
        )
