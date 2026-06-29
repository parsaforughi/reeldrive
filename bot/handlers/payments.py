"""Telegram Stars payments — Pro subscription."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.config import settings
from bot.i18n import require_user_lang, t, tu
from bot.keyboards import subscription_shop_kb
from bot.services.analytics import log_activity
from bot.services.pricing import is_allowed_plan_days, plan_stars
from bot.services.subscription import (
    get_bot_user,
    grant_pro,
    is_ai_unlimited,
    is_plan_active,
    subscription_status_line,
)

logger = logging.getLogger(__name__)

router = Router()

PRO_PAYLOAD = "reeldrive_pro"


def _payload(kind: str, telegram_id: int, days: int | None = None) -> str:
    if days is None:
        days = settings.pro_subscription_days
    return f"{kind}:{telegram_id}:{days}"


def _parse_payload(payload: str, kind: str, telegram_id: int) -> int | None:
    if payload == kind:
        return settings.pro_subscription_days
    prefix = f"{kind}:{telegram_id}"
    if payload == prefix:
        return settings.pro_subscription_days
    if payload.startswith(f"{prefix}:"):
        try:
            days = int(payload.rsplit(":", 1)[-1])
        except ValueError:
            return None
        return days if is_allowed_plan_days(days) else None
    return None


def _valid_payload(payload: str, kind: str, telegram_id: int) -> bool:
    return _parse_payload(payload, kind, telegram_id) is not None


async def send_subscription_shop(
    bot: Bot, chat_id: int, user_id: int, username: str | None = None
) -> None:
    lang = await require_user_lang(user_id)
    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "payments_disabled"))
        return

    user = await get_bot_user(user_id)
    vip = await is_ai_unlimited(user_id, username)
    status = await subscription_status_line(
        user, vip, lang, telegram_id=user_id, username=username
    )

    await bot.send_message(
        chat_id,
        t(
            "shop_body",
            lang,
            name=settings.bot_name,
            pro_stars=settings.pro_stars_price,
            days=settings.pro_subscription_days,
            free_total=settings.free_direct_downloads,
            status=status,
        ),
        reply_markup=subscription_shop_kb(lang),
    )


async def send_pro_invoice(bot: Bot, chat_id: int, user_id: int) -> None:
    lang = await require_user_lang(user_id)
    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "payments_disabled"))
        return

    user = await get_bot_user(user_id)
    if is_plan_active(user) and user and user.subscription_plan in ("download", "pro", "premium"):
        exp = user.subscription_expires_at
        exp_text = exp.strftime("%Y-%m-%d") if exp else "—"
        await bot.send_message(
            chat_id,
            t("pro_already_active", lang, date=exp_text),
            reply_markup=subscription_shop_kb(lang),
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
        payload=_payload(PRO_PAYLOAD, user_id),
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=t("pro_price_label", lang, days=settings.pro_subscription_days),
                amount=settings.pro_stars_price,
            )
        ],
    )


@router.message(Command("subscribe"))
@router.message(Command("shop"))
async def cmd_subscribe(message: Message) -> None:
    await send_subscription_shop(
        message.bot,
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
    )


@router.message(Command("pro"))
async def cmd_pro(message: Message) -> None:
    """Legacy alias — same flow as /subscribe (shop Mini App)."""
    await send_subscription_shop(
        message.bot,
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
    )


@router.callback_query(F.data == "shop:open")
async def cb_shop_open(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.answer()
    await send_subscription_shop(
        callback.bot,
        callback.message.chat.id,
        callback.from_user.id,
        callback.from_user.username,
    )


@router.callback_query(F.data == "pay:pro")
async def cb_pay_pro(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.answer()
    await send_subscription_shop(
        callback.bot,
        callback.message.chat.id,
        callback.from_user.id,
        callback.from_user.username,
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    uid = query.from_user.id
    payload = query.invoice_payload or ""
    lang = await require_user_lang(uid)

    days = _parse_payload(payload, PRO_PAYLOAD, uid)
    ok = (
        settings.stars_payment_enabled
        and query.currency == "XTR"
        and days is not None
        and query.total_amount == plan_stars(days)
    )
    if not ok:
        await query.answer(ok=False, error_message=t("checkout_failed", lang))
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    sp = message.successful_payment
    uid = message.from_user.id
    lang = await require_user_lang(uid)

    if not sp or sp.currency != "XTR":
        return

    payload = sp.invoice_payload or ""
    user_kw = dict(
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    days = _parse_payload(payload, PRO_PAYLOAD, uid)
    if days is not None:
        expected = plan_stars(days)
        if sp.total_amount != expected:
            await message.answer(t("payment_failed", lang))
            return
        expires = await grant_pro(uid, days=days, **user_kw)
        await log_activity(
            uid,
            "payment_stars",
            detail=f"pro {expected} XTR / {days}d",
            meta={"plan": "pro", "stars": sp.total_amount, "days": days},
        )
        await message.answer(
            t(
                "pro_payment_ok",
                lang,
                stars=sp.total_amount,
                days=days,
                date=expires.strftime("%Y-%m-%d %H:%M"),
            ),
            reply_markup=subscription_shop_kb(lang),
        )
        return

    logger.warning("Unknown payment payload uid=%s payload=%s", uid, payload)
    await message.answer(t("payment_failed", lang))
