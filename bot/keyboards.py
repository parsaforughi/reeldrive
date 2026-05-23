from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def connect_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ لغو", callback_data="connect:cancel")
    )
    return builder.as_markup()


def myinstagram_kb(connected: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if connected:
        builder.row(
            InlineKeyboardButton(text="🔌 قطع اتصال", callback_data="ig:disconnect")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔐 اتصال پیج", callback_data="ig:connect")
        )
    builder.row(
        InlineKeyboardButton(text="⚡ دایرکت دانلود", callback_data="menu:directdownload"),
        InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="menu:start"),
    )
    return builder.as_markup()


def settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔐 اتصال پیج", callback_data="ig:connect"),
        InlineKeyboardButton(text="📩 اینستاگرام من", callback_data="menu:myinstagram"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ دایرکت دانلود", callback_data="menu:directdownload"),
        InlineKeyboardButton(text="💬 امکانات", callback_data="menu:help"),
    )
    return builder.as_markup()
