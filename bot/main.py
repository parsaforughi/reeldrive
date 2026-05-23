import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from bot.config import settings
from bot.handlers import setup_routers
from bot.services.instagram import instagram_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(setup_routers())

    logger.info("Connecting to Instagram…")
    connected = await asyncio.to_thread(instagram_service.connect)
    if connected:
        logger.info("Instagram ready")
    else:
        logger.warning(
            "Instagram not configured — set INSTAGRAM_USERNAME/PASSWORD. "
            "Bot will start but downloads will fail until configured."
        )

    logger.info("Starting %s bot (polling)…", settings.bot_name)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
