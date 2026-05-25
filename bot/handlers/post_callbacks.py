import logging

import aiohttp
from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from bot.handlers.download_helpers import send_media_result
from bot.i18n import friendly_error, require_user_lang, tu
from bot.keyboards import qualities_kb
from bot.post_display import PostMeta, format_post_caption
from bot.services.direct_download import download_media_url
from bot.services.post_cache import get_post

router = Router()
logger = logging.getLogger(__name__)
TMP = "/tmp/reeldrive"


@router.callback_query(F.data.startswith("post:"))
async def post_action(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    lang = await require_user_lang(uid)
    data = callback.data or ""
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    code = parts[2] if len(parts) > 2 else None

    if action == "dl" and len(parts) >= 4:
        code = parts[2]
        try:
            index = int(parts[3])
        except ValueError:
            await callback.answer(await tu(uid, "invalid"))
            return
        await _download_variant(callback, code, index, lang)
        return

    if not code:
        await callback.answer(await tu(uid, "invalid"))
        return

    cached = get_post(code)

    if action in ("ai", "subs", "audio"):
        keys = {
            "ai": "coming_soon_ai",
            "subs": "coming_soon_subs",
            "audio": "coming_soon_audio",
        }
        await callback.answer(await tu(uid, keys[action]), show_alert=True)
        return

    if not cached:
        await callback.answer(await tu(uid, "post_expired"), show_alert=True)
        return

    if action == "caption":
        meta = PostMeta(
            short_code=code,
            post_url=cached.source_url,
            caption=str(cached.apify_item.get("caption") or ""),
            hashtags=cached.apify_item.get("hashtags") or [],
        )
        await callback.message.answer(format_post_caption(meta))
        await callback.answer()
        return

    if action == "links":
        variants = cached.variants
        if not variants:
            urls = cached.direct_urls or []
            if not urls:
                await callback.answer(await tu(uid, "no_links_saved"), show_alert=True)
                return
            text = "🌐\n\n" + "\n\n".join(
                f"{i + 1}. {u}" for i, u in enumerate(urls[:10])
            )
        else:
            lines = ["🌐\n"]
            for i, v in enumerate(variants, 1):
                lines.append(f"{i}. <b>{v.label}</b>\n{v.url}")
            text = "\n\n".join(lines)
        await callback.message.answer(text[:4000])
        await callback.answer()
        return

    if action == "qualities":
        variants = cached.variants
        if not variants:
            await callback.answer(await tu(uid, "no_quality"), show_alert=True)
            return
        if len(variants) == 1:
            await callback.message.answer(
                f"<b>{variants[0].label}</b>\n\n"
                + await tu(uid, "post_expired")
            )
            await callback.answer()
            return
        await callback.message.answer(
            "💽\n" + "\n".join(f"{i}. {v.label}" for i, v in enumerate(variants, 1)),
            reply_markup=qualities_kb(code, variants),
        )
        await callback.answer()
        return

    if action == "refresh":
        await callback.answer(await tu(uid, "refreshing"))
        try:
            result = await download_media_url(cached.source_url)
            await send_media_result(callback.message, result)
        except ValueError as exc:
            logger.warning("Post refresh failed: %s", exc)
            await callback.message.answer(friendly_error(exc, lang))
        except Exception:
            logger.exception("Post refresh error")
            await callback.message.answer(await tu(uid, "error_generic"))
        return

    await callback.answer()


async def _download_variant(
    callback: CallbackQuery, code: str, index: int, lang: str
) -> None:
    uid = callback.from_user.id
    cached = get_post(code)
    if not cached or not cached.variants:
        await callback.answer(await tu(uid, "post_expired"), show_alert=True)
        return
    if index < 0 or index >= len(cached.variants):
        await callback.answer(await tu(uid, "invalid"))
        return

    var = cached.variants[index]
    await callback.answer(await tu(uid, "downloading", label=var.label))

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(var.url) as resp:
                if not (200 <= resp.status < 300):
                    await callback.message.answer(await tu(uid, "download_failed"))
                    return
                data = await resp.read()
        ext = ".mp4" if var.kind == "video" else ".jpg"
        path = f"{TMP}/q_{code}_{index}{ext}"
        with open(path, "wb") as f:
            f.write(data)
        cap = f"📥 {var.label}"
        if var.kind == "video":
            await callback.message.answer_video(FSInputFile(path), caption=cap)
        else:
            await callback.message.answer_photo(FSInputFile(path), caption=cap)
    except Exception:
        logger.exception("Variant download failed")
        await callback.message.answer(await tu(uid, "download_error"))
