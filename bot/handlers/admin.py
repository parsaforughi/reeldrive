"""Admin-only commands + following-token purchase approval flow."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import tu
from bot.services.following_access import grant_credits, is_admin, notify_ids

router = Router()
logger = logging.getLogger(__name__)


async def _notify_target_granted(bot: Bot, target_id: int, count: int, balance: int) -> None:
    try:
        await bot.send_message(
            target_id,
            await tu(target_id, "following_tokens_granted_notify", count=count, balance=balance),
        )
    except Exception:
        logger.warning(
            "Could not notify user %s about %s granted tokens", target_id, count, exc_info=True
        )


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
    await _notify_target_granted(message.bot, target_id, count, balance)


def _approve_kb(target_id: int, count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ تأیید پرداخت و فعال‌سازی توکن",
            callback_data=f"following:approve:{target_id}:{count}",
        )
    )
    return builder.as_markup()


async def send_receipt_to_admins(
    bot: Bot,
    target_id: int,
    username: str | None,
    count: int,
    amount: int,
    card: str,
    photo_id: str,
) -> None:
    """Sent once the user actually submits a receipt photo — this is the
    admin's proof to check against the bank account before approving."""
    who = f"@{username}" if username else str(target_id)
    caption = (
        "🧾 رسید خرید توکن فالووینگ\n\n"
        f"کاربر: {who}\n"
        f"شناسه: {target_id}\n"
        f"تعداد: {count}\n"
        f"مبلغ: {amount:,} تومان\n"
        f"کارت مقصد: {card}\n\n"
        "بعد از چک کردن واریزی، روی دکمه زیر بزن:"
    )
    for admin_id in notify_ids():
        try:
            await bot.send_photo(
                admin_id, photo_id, caption=caption, reply_markup=_approve_kb(target_id, count)
            )
        except Exception:
            logger.warning(
                "Could not send receipt to admin %s for token purchase", admin_id, exc_info=True
            )


@router.callback_query(F.data.startswith("following:approve:"))
async def approve_token_purchase(callback: CallbackQuery) -> None:
    admin_uid = callback.from_user.id
    if not is_admin(admin_uid):
        await callback.answer()
        return

    try:
        _, _, target_raw, count_raw = callback.data.split(":")
        target_id = int(target_raw)
        count = int(count_raw)
    except ValueError:
        await callback.answer()
        return

    balance = await grant_credits(target_id, count, granted_by=admin_uid)

    confirmed_line = f"\n\n✅ تأیید شد — موجودی جدید: {balance}"
    if callback.message.photo:
        base_caption = callback.message.caption or ""
        await callback.message.edit_caption(caption=base_caption + confirmed_line, reply_markup=None)
    else:
        base_text = callback.message.text or ""
        await callback.message.edit_text(base_text + confirmed_line, reply_markup=None)

    await callback.answer("تأیید شد")
    await _notify_target_granted(callback.bot, target_id, count, balance)
