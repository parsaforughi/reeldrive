"""Telegram Stars payments for Pro subscription."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.config import settings
from bot.i18n import require_user_lang, t, tu
from bot.keyboards import pro_pay_kb
from bot.services.analytics import log_activity
from bot.services.subscription import get_bot_user, grant_pro, is_plan_active

logger = logging.getLogger(__name__)

router = Router()

PRO_PAYLOAD = "reeldrive_pro"


def _pro_payload(telegram_id: int) -> str:
    return f"{PRO_PAYLOAD}:{telegram_id}"


def _parse_pro_payload(payload: str, telegram_id: int) -> bool:
    if payload == PRO_PAYLOAD:
        return True
    expected = f"{PRO_PAYLOAD}:{telegram_id}"
    return payload == expected


async def send_pro_invoice(bot: Bot, chat_id: int, user_id: int) -> None:
    lang = await require_user_lang(user_id)

    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "pro_disabled"))
        return

    user = await get_bot_user(user_id)
    if is_plan_active(user) and user and user.subscription_plan == "pro":
        exp = user.subscription_expires_at
        exp_text = exp.strftime("%Y-%m-%d") if exp else "—"
        await bot.send_message(
            chat_id,
            t("pro_already_active", lang, date=exp_text),
            reply_markup=pro_pay_kb(lang, renew=True),
        )
        return

    await bot.send_invoice(
        chat_id=chat_id,
        title=t("pro_invoice_title", lang),
        description=t(
            "pro_invoice_desc",
            lang,
            days=settings.pro_subscription_days,
            name=settings.bot_name,
        ),
        payload=_pro_payload(user_id),
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=t("pro_price_label", lang, days=settings.pro_subscription_days),
                amount=settings.pro_stars_price,
            )
        ],
    )


@router.message(Command("pro"))
async def cmd_pro(message: Message) -> None:
    await send_pro_invoice(message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "pay:pro")
async def cb_pay_pro(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.answer()
    await send_pro_invoice(
        callback.bot,
        callback.message.chat.id,
        callback.from_user.id,
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    uid = query.from_user.id
    ok = (
        settings.stars_payment_enabled
        and query.currency == "XTR"
        and query.total_amount == settings.pro_stars_price
        and _parse_pro_payload(query.invoice_payload or "", uid)
    )
    if not ok:
        lang = await require_user_lang(uid)
        await query.answer(
            ok=False,
            error_message=t("pro_checkout_failed", lang),
        )
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    sp = message.successful_payment
    uid = message.from_user.id
    lang = await require_user_lang(uid)

    if not sp or sp.currency != "XTR":
        return
    if sp.total_amount != settings.pro_stars_price:
        logger.warning(
            "Stars amount mismatch uid=%s got=%s expected=%s",
            uid,
            sp.total_amount,
            settings.pro_stars_price,
        )
        await message.answer(t("pro_payment_failed", lang))
        return
    if not _parse_pro_payload(sp.invoice_payload or "", uid):
        logger.warning("Invalid payment payload uid=%s payload=%s", uid, sp.invoice_payload)
        await message.answer(t("pro_payment_failed", lang))
        return

    expires = await grant_pro(
        uid,
        days=settings.pro_subscription_days,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    exp_text = expires.strftime("%Y-%m-%d %H:%M")
    await log_activity(
        uid,
        "payment_stars",
        detail=f"pro {settings.pro_stars_price} XTR",
        meta={
            "stars": sp.total_amount,
            "charge_id": sp.telegram_payment_charge_id,
            "days": settings.pro_subscription_days,
        },
    )
    await message.answer(
        t(
            "pro_payment_ok",
            lang,
            stars=settings.pro_stars_price,
            days=settings.pro_subscription_days,
            date=exp_text,
        )
    )
