from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.instagram import instagram_service
from bot.texts import HELP_EN, HELP_FA, START_EN, START_FA

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_FA)
    await message.answer(START_EN)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_FA)
    await message.answer(HELP_EN)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if instagram_service.is_ready:
        text = (
            "✅ اینستاگرام متصل است.\n"
            "✅ Instagram is connected."
        )
    else:
        text = (
            "❌ اینستاگرام متصل نیست.\n"
            "متغیرهای INSTAGRAM_USERNAME و INSTAGRAM_PASSWORD را در Railway تنظیم کن.\n\n"
            "❌ Instagram not connected.\n"
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in Railway."
        )
    await message.answer(text)
