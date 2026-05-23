from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.media_variants import MediaVariant


def connect_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ لغو", callback_data="connect:cancel")
    )
    return builder.as_markup()


def post_actions_kb(post_url: str, short_code: str) -> InlineKeyboardMarkup:
    code = short_code or "x"
    builder = InlineKeyboardBuilder()
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
            text="🤖 تحلیل پست با هوش مصنوعی 📝",
            callback_data=f"post:ai:{code}",
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
