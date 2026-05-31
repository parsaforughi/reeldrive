import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.config import settings
from bot.db import init_db
from bot.handlers import setup_routers
from bot.menu import setup_bot_menu
from bot.middleware import AnalyticsMiddleware
from bot.middleware.language_gate import LanguageGateMiddleware
from bot.services.bridge_poller import BridgePoller
from bot.services.client_pool import client_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()
    await init_db()
    if settings.database_is_postgres:
        logger.info("Database: PostgreSQL (persistent across deploys)")
    elif os.environ.get("RAILWAY_ENVIRONMENT"):
        vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
        logger.info(
            "Database: SQLite at %s%s",
            settings.persistent_data_dir,
            " (Railway Volume)" if vol else " — add Postgres or Volume /app/data",
        )
    else:
        logger.info("Database: SQLite at %s", settings.persistent_data_dir)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(LanguageGateMiddleware())
    dp.callback_query.middleware(LanguageGateMiddleware())
    dp.message.middleware(AnalyticsMiddleware())
    dp.callback_query.middleware(AnalyticsMiddleware())
    dp.include_router(setup_routers())

    await setup_bot_menu(bot)
    logger.info("Telegram menu commands registered")

    loop = asyncio.get_running_loop()

    from bot.services.apify import apify_downloader

    if apify_downloader.ready:
        logger.info("Apify direct download enabled")
    else:
        logger.warning("APIFY_TOKEN not set — link download will need instagrapi fallback")

    bridge_ok = False
    if settings.instagram_bridge_enabled:
        logger.info("Connecting Instagram bridge account…")
        logger.info("User-facing bridge DM handle: %s", settings.bridge_ig_handle)
        bridge_ok = client_pool.connect_bridge()
    else:
        logger.info("Bridge login disabled (INSTAGRAM_BRIDGE_ENABLED=false)")
    if client_pool.bridge_dm_ready:
        logger.info("Bridge Instagram ready — IG DMs will forward to Telegram")
    elif bridge_ok:
        logger.warning(
            "Bridge session loaded but DM inbox unavailable. "
            "Refresh INSTAGRAM_BRIDGE_SESSION_ID (fresh browser sessionid)."
        )
    else:
        logger.warning(
            "Bridge IG offline — Bio+/verify works; send links in Telegram chat."
        )

    svc_user = (settings.instagram_username or "").strip().lstrip("@").lower()
    br_user = (
        (settings.instagram_bridge_username or settings.instagram_username or "")
        .strip()
        .lstrip("@")
        .lower()
    )
    if bridge_ok and svc_user and svc_user == br_user:
        client_pool.service = client_pool.bridge
        logger.info("Service IG shares bridge session (@%s)", svc_user)
    else:
        logger.info("Connecting Instagram service account (optional)…")
        if client_pool.connect_service():
            logger.info("Service Instagram ready (profile/stories)")
        elif svc_user:
            logger.warning("Service IG login failed — profile/stories unavailable")

    poller = BridgePoller(bot, loop)
    poll_task = asyncio.create_task(poller.run_loop())

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting %s (polling)…", settings.bot_name)
    logger.info(
        "If you see TelegramConflictError: stop the bot on your Mac "
        "(Ctrl+C in terminal) — only one instance may poll."
    )
    try:
        await dp.start_polling(bot)
    finally:
        poller.stop()
        poll_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
