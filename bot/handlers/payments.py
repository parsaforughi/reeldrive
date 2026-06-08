"""Telegram Stars payments — download + Pro subscriptions."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.config import settings
from bot.i18n import require_user_lang, t, tu
from bot.keyboards import subscription_shop_kb
from bot.services.analytics import log_activity
from bot.services.subscription import (
    get_bot_user,
    grant_download,
    grant_pro,
    has_download_access,
    is_ai_unlimited,
    is_plan_active,
    subscription_status_line,
)

logger = logging.getLogger(__name__)

router = Router()

DOWNLOAD_PAYLOAD = "reeldrive_download"
PRO_PAYLOAD = "reeldrive_pro"


def _payload(kind: str, telegram_id: int) -> str:
    return f"{kind}:{telegram_id}"


def _valid_payload(payload: str, kind: str, telegram_id: int) -> bool:
    return payload in (kind, f"{kind}:{telegram_id}")


async def send_subscription_shop(
    bot: Bot, chat_id: int, user_id: int, username: str | None = None
) -> None:
    lang = await require_user_lang(user_id)
    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "payments_disabled"))
        return

    user = await get_bot_user(user_id)
    vip = await is_ai_unlimited(user_id, username)
    status = await subscription_status_line(user, vip, lang)

    await bot.send_message(
        chat_id,
        t(
            "shop_body",
            lang,
            name=settings.bot_name,
            download_stars=settings.download_stars_price,
            pro_stars=settings.pro_stars_price,
            days=settings.download_subscription_days,
            support=f"@{settings.payment_support_username.lstrip('@')}",
            status=status,
        ),
        reply_markup=subscription_shop_kb(lang),
    )


async def send_download_invoice(bot: Bot, chat_id: int, user_id: int) -> None:
    lang = await require_user_lang(user_id)
    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "payments_disabled"))
        return

    user = await get_bot_user(user_id)
    if await has_download_access(user_id) and user and user.subscription_plan in (
        "download",
        "pro",
        "premium",
    ):
        exp = user.subscription_expires_at
        exp_text = exp.strftime("%Y-%m-%d") if exp else "—"
        await bot.send_message(
            chat_id,
            t("download_already_active", lang, date=exp_text),
            reply_markup=subscription_shop_kb(lang),
        )
        return

    await bot.send_invoice(
        chat_id=chat_id,
        title=t("download_invoice_title", lang),
        description=t(
            "download_invoice_desc",
            lang,
            days=settings.download_subscription_days,
            name=settings.bot_name,
        ),
        payload=_payload(DOWNLOAD_PAYLOAD, user_id),
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=t(
                    "download_price_label",
                    lang,
                    days=settings.download_subscription_days,
                ),
                amount=settings.download_stars_price,
            )
        ],
    )


async def send_pro_invoice(bot: Bot, chat_id: int, user_id: int) -> None:
    lang = await require_user_lang(user_id)
    if not settings.stars_payment_enabled:
        await bot.send_message(chat_id, await tu(user_id, "payments_disabled"))
        return

    user = await get_bot_user(user_id)
    if is_plan_active(user) and user and user.subscription_plan == "pro":
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
    await send_pro_invoice(message.bot, message.chat.id, message.from_user.id)


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


@router.callback_query(F.data == "pay:download")
async def cb_pay_download(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.answer()
    await send_download_invoice(
        callback.bot, callback.message.chat.id, callback.from_user.id
    )


@router.callback_query(F.data == "pay:pro")
async def cb_pay_pro(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.answer()
    await send_pro_invoice(callback.bot, callback.message.chat.id, callback.from_user.id)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    uid = query.from_user.id
    payload = query.invoice_payload or ""
    lang = await require_user_lang(uid)

    ok = (
        settings.stars_payment_enabled
        and query.currency == "XTR"
        and (
            (
                _valid_payload(payload, DOWNLOAD_PAYLOAD, uid)
                and query.total_amount == settings.download_stars_price
            )
            or (
                _valid_payload(payload, PRO_PAYLOAD, uid)
                and query.total_amount == settings.pro_stars_price
            )
        )
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

    if _valid_payload(payload, DOWNLOAD_PAYLOAD, uid):
        if sp.total_amount != settings.download_stars_price:
            await message.answer(t("payment_failed", lang))
            return
        expires = await grant_download(uid, days=settings.download_subscription_days, **user_kw)
        await log_activity(
            uid,
            "payment_stars",
            detail=f"download {settings.download_stars_price} XTR",
            meta={"plan": "download", "stars": sp.total_amount, "days": settings.download_subscription_days},
        )
        await message.answer(
            t(
                "download_payment_ok",
                lang,
                stars=settings.download_stars_price,
                days=settings.download_subscription_days,
                date=expires.strftime("%Y-%m-%d %H:%M"),
            ),
            reply_markup=subscription_shop_kb(lang),
        )
        return

    if _valid_payload(payload, PRO_PAYLOAD, uid):
        if sp.total_amount != settings.pro_stars_price:
            await message.answer(t("payment_failed", lang))
            return
        expires = await grant_pro(uid, days=settings.pro_subscription_days, **user_kw)
        await log_activity(
            uid,
            "payment_stars",
            detail=f"pro {settings.pro_stars_price} XTR",
            meta={"plan": "pro", "stars": sp.total_amount, "days": settings.pro_subscription_days},
        )
        await message.answer(
            t(
                "pro_payment_ok",
                lang,
                stars=settings.pro_stars_price,
                days=settings.pro_subscription_days,
                date=expires.strftime("%Y-%m-%d %H:%M"),
            ),
            reply_markup=subscription_shop_kb(lang),
        )
        return

    logger.warning("Unknown payment payload uid=%s payload=%s", uid, payload)
    await message.answer(t("payment_failed", lang))
