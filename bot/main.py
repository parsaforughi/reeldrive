import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.config import settings
from bot.db import init_db
from bot.handlers import setup_routers
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

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    loop = asyncio.get_running_loop()

    logger.info("Connecting Instagram service account…")
    if client_pool.connect_service():
        logger.info("Service Instagram ready")
    else:
        logger.warning("Service IG not configured (INSTAGRAM_USERNAME/PASSWORD)")

    logger.info("Connecting Instagram bridge account…")
    if client_pool.connect_bridge():
        logger.info("Bridge Instagram ready")
    else:
        logger.warning("Bridge IG not configured")

    poller = BridgePoller(bot, loop)
    poll_task = asyncio.create_task(poller.run_loop())

    logger.info("Starting %s (polling)…", settings.bot_name)
    try:
        await dp.start_polling(bot)
    finally:
        poller.stop()
        poll_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
