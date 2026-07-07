from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.i18n import require_user_lang, t
from bot.media_variants import MediaVariant


def _ai_analyze_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="🤖 تحلیل پست با هوش مصنوعی 📝",
        callback_data=callback_data,
        style=ButtonStyle.PRIMARY,
    )


def language_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang:fa"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    )
    builder.row(
        InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang:ar"),
    )
    return builder.as_markup()


async def connect_cancel_kb(telegram_id: int) -> InlineKeyboardMarkup:
    lang = await require_user_lang(telegram_id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_cancel", lang),
            callback_data="connect:cancel",
        )
    )
    return builder.as_markup()


async def following_cancel_kb(telegram_id: int) -> InlineKeyboardMarkup:
    lang = await require_user_lang(telegram_id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_cancel", lang),
            callback_data="following:cancel",
        )
    )
    return builder.as_markup()


def subscription_shop_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_open_shop", lang),
            web_app=WebAppInfo(url=settings.shop_webapp_url),
        )
    )
    return builder.as_markup()


def paywall_kb(lang: str) -> InlineKeyboardMarkup:
    return subscription_shop_kb(lang)


def pro_pay_kb(lang: str, *, renew: bool = False) -> InlineKeyboardMarkup | None:
    return subscription_shop_kb(lang)


def video_analyze_kb(file_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_ai_analyze_button(f"analyze:file:{file_id}"))
    return builder.as_markup()


def post_actions_kb(post_url: str, short_code: str) -> InlineKeyboardMarkup:
    code = short_code or "x"
    builder = InlineKeyboardBuilder()
    builder.row(_ai_analyze_button(f"post:ai:{code}"))
    builder.row(
        InlineKeyboardButton(
            text="• مشاهده در اینستاگرام ↗️",
            url=post_url,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 بروزرسانی اطلاعات پست",
            callback_data=f"post:refresh:{code}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💬 زیرنویس ویدیو (آزمایشی) 🎬",
            callback_data=f"post:subs:{code}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💽 مشاهده همه کیفیت ها",
            callback_data=f"post:qualities:{code}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔊 دانلود صدای ویدیو",
            callback_data=f"post:audio:{code}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🌐 دریافت لینک دانلود",
            callback_data=f"post:links:{code}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📜 دریافت کپشن",
            callback_data=f"post:caption:{code}",
        )
    )
    return builder.as_markup()


def qualities_kb(short_code: str, variants: list[MediaVariant]) -> InlineKeyboardMarkup:
    """One download button per available quality/variant."""
    builder = InlineKeyboardBuilder()
    for i, var in enumerate(variants[:8]):
        icon = "🎬" if var.kind == "video" else "🖼"
        text = f"{icon} {var.label}"[:60]
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"post:dl:{short_code}:{i}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🌐 همه لینک‌ها",
            callback_data=f"post:links:{short_code}",
        )
    )
    return builder.as_markup()
