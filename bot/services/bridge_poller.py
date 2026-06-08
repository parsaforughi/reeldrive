import asyncio
import logging
from dataclasses import dataclass, field

from aiogram import Bot

from bot.config import settings
from bot.handlers.download_helpers import deliver_media_result
from bot.i18n import require_user_lang, t
from bot.keyboards import paywall_kb
from bot.post_display import post_meta_from_url
from bot.services.apify import apify_downloader
from bot.services.cdn_download import download_cdn_files
from bot.services.client_pool import client_pool
from bot.services.instagram import MediaResult
from bot.services.subscription import has_pro_access
from bot.services.verification import (
    confirm_connection,
    extract_verification_code,
    get_connected_by_ig_user_id,
    get_pending_by_code,
)
from bot.utils import parse_media_url

logger = logging.getLogger(__name__)


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
        self._pending_tasks: set[asyncio.Task] = set()

    async def run_loop(self) -> None:
        self._running = True
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

    def _fetch_new_messages(self) -> list[BridgeMessage]:
        web = client_pool.bridge_web
        if not web:
            return []

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

        # Same pipeline as pasting a link in Telegram chat (Apify + caption + buttons).
        ig_url = item.media_url or parse_media_url(text)
        if ig_url or item.media_files:
            if not await has_pro_access(chat_id):
                lang = await require_user_lang(chat_id)
                await self._bot.send_message(
                    chat_id,
                    t(
                        "pro_paywall",
                        lang,
                        pro_stars=settings.pro_stars_price,
                    ),
                    reply_markup=paywall_kb(lang),
                )
                return
            await self._download_and_send(chat_id, ig_url, item.media_files)
            return

        await self._forward_plain_text(chat_id, text)

    async def _forward_plain_text(self, telegram_id: int, text: str) -> None:
        if not text.strip():
            return
        lang = await require_user_lang(telegram_id)
        prefix = t("forward_ig_prefix", lang)
        await self._bot.send_message(telegram_id, f"{prefix}{text}")

    async def _download_and_send(
        self,
        chat_id: int,
        url: str,
        media_files: list[tuple[str, bool]] | None = None,
    ) -> None:
        apify_item: dict | None = None
        normalized = url
        results_type = "posts"
        variants: list = []
        paths: list = []

        if url and apify_downloader.ready:
            try:
                normalized, results_type, apify_item, variants = (
                    await apify_downloader.scrape_media_url(url)
                )
                paths = await apify_downloader.download_variants(variants)
                if not paths:
                    logger.warning(
                        "Bridge Apify CDN download failed for %s — trying DM payload",
                        url,
                    )
            except ValueError as exc:
                logger.warning("Bridge Apify scrape failed: %s", exc)

        if not paths and media_files:
            paths = await download_cdn_files(media_files)

        if not paths:
            lang = await require_user_lang(chat_id)
            await self._bot.send_message(chat_id, t("error_not_found", lang))
            return

        if apify_item and variants:
            result = apify_downloader.build_media_result(
                apify_item, normalized, results_type, paths, variants
            )
        else:
            direct_urls = [u for u, _ in media_files] if media_files else []
            result = MediaResult(
                paths=paths,
                caption="",
                media_type="reels" if any(v for _, v in (media_files or [])) else "posts",
                direct_urls=direct_urls,
                post_meta=post_meta_from_url(url) if url else None,
                source_url=url,
            )

        await deliver_media_result(self._bot, chat_id, result)
