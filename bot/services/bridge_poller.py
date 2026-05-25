import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot

from bot.config import settings
from bot.services.client_pool import client_pool
from bot.handlers.download_helpers import deliver_media_result
from bot.services.direct_download import download_media_url
from bot.services.verification import (
    confirm_connection,
    get_connected_by_ig_user_id,
    get_pending_by_code,
)
from bot.utils import parse_media_url

logger = logging.getLogger(__name__)

INSTAGRAM_URL_IN_TEXT = re.compile(
    r"https?://(?:www\.)?instagram\.com/[^\s]+", re.IGNORECASE
)


@dataclass
class BridgeMessage:
    thread_id: str
    message_id: str
    user_id: str
    username: str | None
    text: str


class BridgePoller:
    def __init__(self, bot: Bot, loop: asyncio.AbstractEventLoop) -> None:
        self._bot = bot
        self._loop = loop
        self._seen: set[str] = set()
        self._running = False

    async def run_loop(self) -> None:
        self._running = True
        while self._running:
            try:
                batch = await asyncio.to_thread(self._fetch_new_messages)
                for item in batch:
                    await self._handle_message(item)
            except Exception:
                logger.exception("Bridge poll error")
            await asyncio.sleep(settings.bridge_poll_interval_seconds)

    def stop(self) -> None:
        self._running = False

    def _fetch_new_messages(self) -> list[BridgeMessage]:
        client = client_pool.bridge
        if not client:
            return []

        out: list[BridgeMessage] = []
        threads = client.direct_threads(amount=30)
        for thread in threads:
            try:
                messages = client.direct_messages(thread.id, amount=15)
            except Exception:
                continue
            users = {u.pk: u.username for u in (thread.users or [])}
            for msg in messages:
                key = f"{thread.id}:{msg.id}"
                if key in self._seen:
                    continue
                self._seen.add(key)
                if len(self._seen) > 5000:
                    self._seen = set(list(self._seen)[-2000:])
                text = (msg.text or "").strip()
                if not text:
                    continue
                out.append(
                    BridgeMessage(
                        thread_id=str(thread.id),
                        message_id=str(msg.id),
                        user_id=str(msg.user_id),
                        username=users.get(msg.user_id),
                        text=text,
                    )
                )
        return out

    async def _handle_message(self, item: BridgeMessage) -> None:
        text = item.text

        pending = await get_pending_by_code(text)
        if pending and item.username:
            if item.username.lower() != pending.instagram_username.lower():
                return
            await confirm_connection(
                pending.telegram_id,
                item.user_id,
                item.username,
            )
            from bot.i18n import require_user_lang, t

            lang = await require_user_lang(pending.telegram_id)
            await self._bot.send_message(
                pending.telegram_id,
                t(
                    "connected_ok",
                    lang,
                    username=item.username,
                    bridge=settings.bridge_ig_handle,
                ),
            )
            return

        conn = await get_connected_by_ig_user_id(item.user_id)
        if not conn:
            return

        await self._forward_to_telegram(conn.telegram_id, text)

    async def _forward_to_telegram(self, telegram_id: int, text: str) -> None:
        from bot.i18n import require_user_lang, t

        lang = await require_user_lang(telegram_id)
        prefix = t("forward_ig_prefix", lang)
        urls = INSTAGRAM_URL_IN_TEXT.findall(text)

        if urls:
            await self._bot.send_message(telegram_id, f"{prefix}{text[:900]}")
            for url in urls:
                await self._download_and_send(telegram_id, url)
            return

        media_url = parse_media_url(text)
        if media_url:
            await self._download_and_send(telegram_id, media_url)
            return

        await self._bot.send_message(telegram_id, f"{prefix}{text}")

    async def _download_and_send(self, chat_id: int, url: str) -> None:
        try:
            result = await download_media_url(url)
            await deliver_media_result(self._bot, chat_id, result)
        except ValueError as exc:
            await self._bot.send_message(chat_id, f"❌ {exc}")
