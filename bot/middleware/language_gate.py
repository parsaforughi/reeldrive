from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.i18n import get_user_lang, t
from bot.keyboards import language_kb


class LanguageGateMiddleware(BaseMiddleware):
    """Ask new users to pick a language before other handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and not user.is_bot:
            if await get_user_lang(user.id):
                return await handler(event, data)

            if isinstance(event, CallbackQuery) and (event.data or "").startswith(
                "lang:"
            ):
                return await handler(event, data)

            if isinstance(event, Message) and event.text:
                cmd = event.text.split()[0].split("@")[0].lower()
                if cmd in ("/start", "/language", "/pro", "/subscribe"):
                    return await handler(event, data)

            if isinstance(event, Message) and event.successful_payment:
                return await handler(event, data)

            if isinstance(event, Message):
                await event.answer(
                    t("choose_language", "fa"),
                    reply_markup=language_kb(),
                )
                return None

            if isinstance(event, CallbackQuery):
                await event.answer(
                    t("choose_language", "fa"),
                    show_alert=True,
                )
                return None

        return await handler(event, data)
