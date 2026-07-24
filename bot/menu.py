from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

# منوی آبی تلگرام — مشابه Regrambot (بدون اشتراک ویژه)
BOT_COMMANDS: list[tuple[str, str]] = [
    ("start", "🏠 منوی اصلی / Home"),
    ("language", "🌐 زبان / Language"),
    ("connect", "🔐 اتصال پیج اینستاگرام"),
    ("advancedconnect", "🔓 اتصال پیشرفته پیج"),
    ("verify", "✅ تأیید اتصال (Bio)"),
    ("directdownload", "⚡ دایرکت دانلود"),
    ("subscribe", "⭐ اشتراک Pro"),
    ("myinstagram", "📩 اینستاگرام من"),
    ("search", "🔍 جستجو در اینستاگرام"),
    ("following", "➡️ فالووینگ‌های آیدی"),
    ("unfollowers", "🚶‍♂️ آنفالویاب"),
    ("feed", "🗄️ فید"),
    ("settings", "⚙️ تنظیمات ربات"),
    ("help", "💬 امکانات ربات"),
    ("privacy", "Privacy policy"),
]


async def setup_bot_menu(bot: Bot) -> None:
    commands = [
        BotCommand(command=cmd, description=desc) for cmd, desc in BOT_COMMANDS
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
