import asyncio
import logging
import re
from dataclasses import dataclass

from aiogram import Bot

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
        self._bootstrapped = False
        self._idle_ticks = 0
        self._inbox_blocked_logged = False

    async def run_loop(self) -> None:
        self._running = True
        while self._running:
            try:
                if not client_pool.bridge_ready:
                    self._idle_ticks += 1
                    if self._idle_ticks == 1 or self._idle_ticks % 15 == 0:
                        logger.warning(
                            "Bridge poller idle — set INSTAGRAM_BRIDGE_SESSION_ID"
                        )
                elif not client_pool.bridge_inbox_ok:
                    self._idle_ticks += 1
                    if not self._inbox_blocked_logged:
                        self._inbox_blocked_logged = True
                        logger.warning(
                            "Bridge poller idle — inbox blocked (467). "
                            "Set INSTAGRAM_PROXY on Railway (residential proxy)."
                        )
                else:
                    self._idle_ticks = 0
                    self._inbox_blocked_logged = False
                    batch = await asyncio.to_thread(self._fetch_new_messages)
                    for item in batch:
                        await self._handle_message(item)
            except Exception:
                logger.exception("Bridge poll error")
            await asyncio.sleep(settings.bridge_poll_interval_seconds)

    def stop(self) -> None:
        self._running = False

    def _resolve_username(self, client, user_id: str, thread_users: dict[str, str | None]) -> str | None:
        name = thread_users.get(str(user_id))
        if name:
            return name
        try:
            info = client.user_info(int(user_id))
            return info.username
        except Exception:
            logger.warning("Could not resolve IG username for user_id=%s", user_id)
            return None

    def _fetch_new_messages(self) -> list[BridgeMessage]:
        client = client_pool.bridge
        if not client:
            return []

        out: list[BridgeMessage] = []
        try:
            threads = client.direct_threads(amount=30)
        except Exception as exc:
            client_pool.bridge_inbox_ok = False
            if "467" in str(exc) and not self._inbox_blocked_logged:
                self._inbox_blocked_logged = True
                logger.warning(
                    "IG inbox blocked from server IP (467). "
                    "Set INSTAGRAM_PROXY=http://user:pass@host:port on Railway."
                )
            return []
        for thread in threads:
            try:
                messages = client.direct_messages(thread.id, amount=15)
            except Exception:
                logger.exception("Failed to read DM thread %s", thread.id)
                continue

            thread_users: dict[str, str | None] = {}
            for u in thread.users or []:
                thread_users[str(u.pk)] = u.username

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

                # On first run skip old chatter, but still pick up verification codes
                if not self._bootstrapped and not extract_verification_code(text):
                    continue

                out.append(
                    BridgeMessage(
                        thread_id=str(thread.id),
                        message_id=str(msg.id),
                        user_id=str(msg.user_id),
                        username=self._resolve_username(
                            client, str(msg.user_id), thread_users
                        ),
                        text=text,
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
                client = client_pool.bridge
                if client:
                    sender = await asyncio.to_thread(
                        self._resolve_username, client, item.user_id, {}
                    )

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

        await self._forward_to_telegram(conn.telegram_id, text)

    async def _forward_to_telegram(self, telegram_id: int, text: str) -> None:
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
            logger.warning("Bridge forward download failed: %s", exc)
            lang = await require_user_lang(chat_id)
            await self._bot.send_message(chat_id, t("error_not_found", lang))
