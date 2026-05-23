from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings


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
