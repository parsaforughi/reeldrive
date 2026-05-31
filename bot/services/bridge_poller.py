import asyncio
import logging
import re
from dataclasses import dataclass, field

import aiohttp
from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.config import settings
from bot.handlers.download_helpers import deliver_media_result
from bot.i18n import require_user_lang, t
from bot.services.client_pool import client_pool
from bot.services.direct_download import download_media_url
from bot.services.verification import (
    confirm_connection,
    extract_verification_code,
    get_connected_by_ig_user_id,
    get_pending_by_code,
)
from bot.utils import parse_media_url

logger = logging.getLogger(__name__)

INSTAGRAM_URL_IN_TEXT = re.compile(
    r"https?://(?:www\.)?instagram\.com/[^\s]+", re.IGNORECASE
)

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class BridgeMessage:
    thread_id: str
    message_id: str
    user_id: str
    username: str | None
    text: str
    media_url: str = ""
    media_files: list[tuple[str, bool]] = field(default_factory=list)


class BridgePoller:
    def __init__(self, bot: Bot, loop: asyncio.AbstractEventLoop) -> None:
        self._bot = bot
        self._loop = loop
        self._seen: set[str] = set()
        self._running = False
        self._bootstrapped = False
        self._idle_ticks = 0
        self._inbox_blocked_logged = False
        self._last_inbox_seq: str = ""
        self._http: aiohttp.ClientSession | None = None
        self._pending_tasks: set[asyncio.Task] = set()

    async def _ensure_http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            timeout = aiohttp.ClientTimeout(total=90, connect=10)
            self._http = aiohttp.ClientSession(timeout=timeout, headers=_FETCH_HEADERS)
        return self._http

    async def run_loop(self) -> None:
        self._running = True
        await self._ensure_http()
        while self._running:
            interval = settings.bridge_poll_interval_seconds
            try:
                if not client_pool.bridge_ready:
                    self._idle_ticks += 1
                    interval = settings.bridge_poll_idle_seconds
                    if self._idle_ticks == 1 or self._idle_ticks % 15 == 0:
                        logger.warning(
                            "Bridge poller idle — set INSTAGRAM_BRIDGE_SESSION_ID"
                        )
                elif not client_pool.bridge_inbox_ok:
                    self._idle_ticks += 1
                    interval = settings.bridge_poll_idle_seconds
                    if not self._inbox_blocked_logged:
                        self._inbox_blocked_logged = True
                        logger.warning(
                            "Bridge poller idle — DM inbox unavailable. "
                            "Refresh INSTAGRAM_BRIDGE_SESSION_ID."
                        )
                else:
                    self._idle_ticks = 0
                    self._inbox_blocked_logged = False
                    batch = await asyncio.to_thread(self._fetch_new_messages)
                    for item in batch:
                        self._spawn(self._handle_message(item))
            except Exception:
                logger.exception("Bridge poll error")
            await asyncio.sleep(interval)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def stop(self) -> None:
        self._running = False
        if self._http and not self._http.closed:
            asyncio.create_task(self._http.close())

    def _fetch_new_messages(self) -> list[BridgeMessage]:
        web = client_pool.bridge_web
        if not web:
            return []

        # Fast path: skip full inbox if IG reports no new activity (~100ms).
        if self._bootstrapped:
            seq, _badge = web.peek_activity()
            if seq and seq == self._last_inbox_seq:
                return []

        out: list[BridgeMessage] = []
        try:
            threads = web.fetch_threads(limit=12, thread_message_limit=5)
            seq, _ = web.peek_activity()
            if seq:
                self._last_inbox_seq = seq
        except Exception as exc:
            client_pool.bridge_inbox_ok = False
            if not self._inbox_blocked_logged:
                self._inbox_blocked_logged = True
                logger.warning(
                    "IG web inbox read failed (%s). Refresh INSTAGRAM_BRIDGE_SESSION_ID.",
                    exc,
                )
            return []

        for thread in threads:
            for item in thread.items:
                if item.is_sent_by_viewer:
                    continue
                key = f"{thread.thread_id}:{item.item_id}"
                if key in self._seen:
                    continue
                self._seen.add(key)
                if len(self._seen) > 5000:
                    self._seen = set(list(self._seen)[-2000:])

                text = item.text.strip()
                media_url = item.media_url
                if not text and not media_url and not item.media_files:
                    continue

                # On first run skip old chatter, but still pick up verification codes
                if not self._bootstrapped and not extract_verification_code(text):
                    continue

                out.append(
                    BridgeMessage(
                        thread_id=thread.thread_id,
                        message_id=item.item_id,
                        user_id=item.user_id,
                        username=thread.users.get(item.user_id),
                        text=text,
                        media_url=media_url,
                        media_files=item.media_files,
                    )
                )

        if not self._bootstrapped:
            self._bootstrapped = True
            logger.info(
                "Bridge DM bootstrap done (%s threads, only new messages processed)",
                len(threads),
            )

        if out:
            logger.info("Bridge received %s new DM(s)", len(out))

        return out

    async def _handle_message(self, item: BridgeMessage) -> None:
        text = item.text
        code = extract_verification_code(text)

        if code:
            pending = await get_pending_by_code(code)
            if not pending:
                logger.info("DM code %s — no matching pending connection", code)
                return

            sender = item.username
            if not sender:
                logger.error(
                    "DM code %s matched pending @%s but sender username unknown",
                    code,
                    pending.instagram_username,
                )
                return

            expected = pending.instagram_username.lower()
            if sender.lower() != expected:
                logger.warning(
                    "DM code %s from @%s but expected @%s (telegram %s)",
                    code,
                    sender,
                    expected,
                    pending.telegram_id,
                )
                lang = await require_user_lang(pending.telegram_id)
                await self._bot.send_message(
                    pending.telegram_id,
                    t(
                        "connect_wrong_account",
                        lang,
                        expected=expected,
                        got=sender,
                    ),
                )
                return

            await confirm_connection(
                pending.telegram_id,
                item.user_id,
                sender,
            )
            lang = await require_user_lang(pending.telegram_id)
            logger.info(
                "Connected telegram %s to @%s via DM code",
                pending.telegram_id,
                sender,
            )
            await self._bot.send_message(
                pending.telegram_id,
                t(
                    "connected_ok",
                    lang,
                    username=sender,
                    bridge=settings.bridge_ig_handle,
                ),
            )
            return

        conn = await get_connected_by_ig_user_id(item.user_id)
        if not conn:
            return

        chat_id = conn.telegram_id

        # Shared reel/post: CDN URL in payload — send ASAP.
        if item.media_files and await self._send_payload_media(chat_id, item.media_files):
            return

        if item.media_url:
            await self._download_and_send(chat_id, item.media_url)
            return

        await self._forward_to_telegram(chat_id, text)

    async def _forward_to_telegram(self, telegram_id: int, text: str) -> None:
        lang = await require_user_lang(telegram_id)
        prefix = t("forward_ig_prefix", lang)
        urls = INSTAGRAM_URL_IN_TEXT.findall(text)

        if urls:
            self._spawn(self._bot.send_message(telegram_id, f"{prefix}{text[:900]}"))
            for url in urls:
                self._spawn(self._download_and_send(telegram_id, url))
            return

        media_url = parse_media_url(text)
        if media_url:
            await self._download_and_send(telegram_id, media_url)
            return

        await self._bot.send_message(telegram_id, f"{prefix}{text}")

    async def _send_payload_media(
        self, chat_id: int, files: list[tuple[str, bool]]
    ) -> bool:
        """Send shared reel/post media. Tries Telegram URL fetch first (fastest)."""
        sent = 0
        for url, is_video in files:
            if await self._try_send_by_url(chat_id, url, is_video):
                sent += 1
                continue
            data = await self._fetch_bytes(url)
            if not data:
                continue
            try:
                if is_video:
                    await self._bot.send_video(
                        chat_id, BufferedInputFile(data, "reel.mp4")
                    )
                else:
                    await self._bot.send_photo(
                        chat_id, BufferedInputFile(data, "image.jpg")
                    )
                sent += 1
            except Exception as exc:
                logger.warning("Failed to send payload media to %s: %s", chat_id, exc)
        return sent > 0

    async def _try_send_by_url(self, chat_id: int, url: str, is_video: bool) -> bool:
        """Let Telegram servers fetch the CDN file — often arrives in 1–2s."""
        try:
            if is_video:
                await self._bot.send_video(chat_id, video=url)
            else:
                await self._bot.send_photo(chat_id, photo=url)
            return True
        except Exception:
            return False

    async def _fetch_bytes(self, url: str) -> bytes | None:
        try:
            session = await self._ensure_http()
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning("Media fetch HTTP %s for %s", resp.status, url[:60])
                    return None
                return await resp.read()
        except Exception as exc:
            logger.warning("Media fetch error: %s", exc)
            return None

    async def _download_and_send(self, chat_id: int, url: str) -> None:
        try:
            result = await download_media_url(url)
            await deliver_media_result(self._bot, chat_id, result)
        except ValueError as exc:
            logger.warning("Bridge forward download failed: %s", exc)
            lang = await require_user_lang(chat_id)
            await self._bot.send_message(chat_id, t("error_not_found", lang))
