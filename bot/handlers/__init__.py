from aiogram import Router

from bot.handlers.commands import router as commands_router
from bot.handlers.messages import router as messages_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(commands_router)
    root.include_router(messages_router)
    return root
