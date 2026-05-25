from aiogram import Router

from bot.handlers.commands import router as commands_router
from bot.handlers.connect import router as connect_router
from bot.handlers.language import router as language_router
from bot.handlers.messages import router as messages_router
from bot.handlers.post_callbacks import router as post_callbacks_router
from bot.handlers.watchlist import router as watchlist_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(language_router)
    root.include_router(commands_router)
    root.include_router(connect_router)
    root.include_router(post_callbacks_router)
    root.include_router(watchlist_router)
    root.include_router(messages_router)
    return root
