from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔗 اتصال پیج")
    builder.button(text="📥 دانلود")
    builder.button(text="📖 راهنما")
    builder.button(text="ℹ️ وضعیت")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def connect_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ لغو", callback_data="connect:cancel")
    )
    return builder.as_markup()
