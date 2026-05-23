from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.services.analytics import event_summary, log_activity, touch_user


class AnalyticsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.types import CallbackQuery, Message

        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and not user.is_bot:
            event_type, detail, meta = await event_summary(event)
            await touch_user(
                user,
                event_type="command" if event_type == "command" else "message",
            )
            await log_activity(user.id, event_type, detail=detail, meta=meta or None)

        return await handler(event, data)
