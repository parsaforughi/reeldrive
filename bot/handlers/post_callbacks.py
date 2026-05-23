import aiohttp
from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from bot.keyboards import qualities_kb
from bot.post_display import PostMeta, format_post_caption
from bot.services.direct_download import download_media_url
from bot.services.post_cache import get_post
from bot.handlers.download_helpers import send_media_result

router = Router()
TMP = "/tmp/reeldrive"


def _code_from_callback(data: str) -> str | None:
    parts = data.split(":")
    if len(parts) >= 3 and parts[0] == "post":
        return parts[2]
    return None


@router.callback_query(F.data.startswith("post:"))
async def post_action(callback: CallbackQuery) -> None:
    data = callback.data or ""
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    code = parts[2] if len(parts) > 2 else None

    if action == "dl" and len(parts) >= 4:
        code = parts[2]
        try:
            index = int(parts[3])
        except ValueError:
            await callback.answer("نامعتبر")
            return
        await _download_variant(callback, code, index)
        return

    if not code:
        await callback.answer("نامعتبر")
        return

    cached = get_post(code)

    if action in ("ai", "subs", "audio"):
        msgs = {
            "ai": "به‌زودی — تحلیل هوش مصنوعی",
            "subs": "به‌زودی — زیرنویس ویدیو",
            "audio": "به‌زودی — دانلود صدا",
        }
        await callback.answer(msgs[action], show_alert=True)
        return

    if not cached:
        await callback.answer(
            "اطلاعات پست منقضی شده — لینک را دوباره بفرست", show_alert=True
        )
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
                await callback.answer("لینکی ذخیره نشده", show_alert=True)
                return
            text = "🌐 لینک‌های دانلود:\n\n" + "\n\n".join(
                f"{i + 1}. {u}" for i, u in enumerate(urls[:10])
            )
        else:
            lines = ["🌐 لینک‌های دانلود:\n"]
            for i, v in enumerate(variants, 1):
                lines.append(f"{i}. <b>{v.label}</b>\n{v.url}")
            text = "\n\n".join(lines)
        await callback.message.answer(text[:4000])
        await callback.answer()
        return

    if action == "qualities":
        variants = cached.variants
        if not variants:
            await callback.answer("کیفیتی یافت نشد", show_alert=True)
            return
        if len(variants) == 1:
            await callback.message.answer(
                f"فقط یک نسخه از Apify برگشت:\n<b>{variants[0].label}</b>\n\n"
                "برای چند کیفیت، لینک را دوباره بفرست یا 🔄 بروزرسانی بزن."
            )
            await callback.answer()
            return
        lines = ["💽 <b>همه کیفیت‌ها</b> — یکی را بزن تا دانلود شود:\n"]
        for i, v in enumerate(variants, 1):
            lines.append(f"{i}. {v.label}")
        await callback.message.answer(
            "\n".join(lines),
            reply_markup=qualities_kb(code, variants),
        )
        await callback.answer()
        return

    if action == "refresh":
        await callback.answer("⏳ در حال بروزرسانی…")
        try:
            result = await download_media_url(cached.source_url)
            await send_media_result(callback.message, result)
        except ValueError as exc:
            await callback.message.answer(f"❌ {exc}")
        return

    await callback.answer()


async def _download_variant(callback: CallbackQuery, code: str, index: int) -> None:
    cached = get_post(code)
    if not cached or not cached.variants:
        await callback.answer("منقضی شده — لینک را دوباره بفرست", show_alert=True)
        return
    if index < 0 or index >= len(cached.variants):
        await callback.answer("نامعتبر")
        return

    var = cached.variants[index]
    await callback.answer(f"⏳ دانلود {var.label}…")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(var.url) as resp:
                if not (200 <= resp.status < 300):
                    await callback.message.answer(f"❌ دانلود ناموفق ({resp.status})")
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
        await callback.message.answer(
            f"❌ خطا در دانلود.\nلینک مستقیم:\n{var.url[:500]}"
        )
