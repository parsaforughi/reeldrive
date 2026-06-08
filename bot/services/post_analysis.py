"""AI post analysis with optional vision + page benchmark."""

import base64
import logging
from datetime import timedelta
from statistics import mean

import aiohttp
from sqlalchemy import func, select

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import ActivityLog
from bot.media_variants import MediaVariant
from bot.post_display import post_meta_from_apify
from bot.services.ai_client import ai_client
from bot.services.analytics import log_activity
from bot.services.apify import apify_downloader
from bot.services.cdn_download import IG_CDN_HEADERS
from bot.services.post_cache import CachedPost
from bot.services.subscription import get_bot_user, is_ai_unlimited, is_plan_active
from bot.services.video_frames import _is_video_item, extract_vision_frames, ffmpeg_ready
from bot.time_utils import utc_now

logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = 750_000


def _metric(item: dict, *keys: str) -> int:
    for key in keys:
        val = item.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return 0


def preview_image_url(item: dict, variants: list[MediaVariant]) -> str | None:
    for key in ("displayUrl", "thumbnailUrl", "display_url", "thumbnail_url"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith("http"):
            if _is_video_url(val):
                continue
            return val
    images = item.get("images") or item.get("imageUrls") or []
    if isinstance(images, list):
        for entry in images:
            if isinstance(entry, str) and entry.startswith("http"):
                return entry
    for var in variants:
        if var.kind == "image":
            return var.url
    return None


def _is_video_url(url: str) -> bool:
    lower = url.lower().split("?")[0]
    return lower.endswith(".mp4") or lower.endswith(".mov")


async def _download_image_b64(url: str) -> tuple[str, str] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=IG_CDN_HEADERS) as resp:
                if not (200 <= resp.status < 300):
                    return None
                data = await resp.read()
                if not data or len(data) > _MAX_IMAGE_BYTES:
                    return None
                ctype = (resp.content_type or "image/jpeg").split(";")[0]
                if "png" in ctype:
                    mime = "image/png"
                elif "webp" in ctype:
                    mime = "image/webp"
                else:
                    mime = "image/jpeg"
                return base64.b64encode(data).decode("ascii"), mime
    except Exception:
        logger.exception("Vision image download failed")
        return None


async def _count_ai_usage(telegram_id: int) -> int:
    since = utc_now() - timedelta(days=30)
    async with async_session() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.telegram_id == telegram_id,
                ActivityLog.event_type == "ai_analysis",
                ActivityLog.created_at >= since,
            )
        )
        return int(count or 0)


async def check_ai_access(
    telegram_id: int, username: str | None = None
) -> tuple[bool, str]:
    if not ai_client.ready:
        return False, "ai_not_configured"
    if await is_ai_unlimited(telegram_id, username):
        return True, ""

    user = await get_bot_user(telegram_id)
    pro = is_plan_active(user) and user and user.subscription_plan in ("pro", "premium")
    if settings.ai_analysis_requires_pro and not pro:
        return False, "ai_pro_required"
    limit = settings.ai_pro_monthly_limit if pro else settings.ai_free_monthly_limit
    if limit > 0:
        used = await _count_ai_usage(telegram_id)
        if used >= limit:
            return False, "ai_limit_reached"
    return True, ""


async def _page_benchmark(username: str, *, exclude_code: str = "") -> dict | None:
    if not settings.ai_page_benchmark_enabled or not apify_downloader.ready:
        return None
    handle = username.strip().lstrip("@").lower()
    if not handle:
        return None
    try:
        url = f"https://www.instagram.com/{handle}/"
        payload = {
            "directUrls": [url],
            "resultsType": "posts",
            "resultsLimit": settings.ai_page_posts_for_avg,
        }
        posts = await apify_downloader._run_actor(payload)
    except Exception:
        logger.warning("Page benchmark scrape failed for @%s", handle)
        return None

    likes: list[int] = []
    comments: list[int] = []
    views: list[int] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        code = str(post.get("shortCode") or post.get("id") or "")
        if exclude_code and code == exclude_code:
            continue
        likes.append(_metric(post, "likesCount", "likes"))
        comments.append(_metric(post, "commentsCount", "comments"))
        views.append(_metric(post, "videoViewCount", "playCount", "videoPlayCount"))

    if not likes:
        return None

    return {
        "sample_size": len(likes),
        "avg_likes": round(mean(likes), 1),
        "avg_comments": round(mean(comments), 1) if comments else 0,
        "avg_views": round(mean(views), 1) if views else 0,
    }


def _build_metrics_text(
    item: dict,
    source_url: str,
    benchmark: dict | None,
    *,
    video_mode: bool = False,
) -> str:
    meta = post_meta_from_apify(item, source_url)
    caption = (meta.caption or "")[:400] if video_mode else (meta.caption or "")[:1500]
    lines = [
        f"Post URL: {meta.post_url}",
        f"Username: @{meta.username}" if meta.username else "",
        f"Likes: {meta.likes}",
        f"Comments: {meta.comments}",
        f"Views: {meta.views}",
        f"Shares: {meta.shares}",
        f"Type: {item.get('type') or item.get('productType') or 'unknown'}",
        f"Timestamp: {meta.timestamp_iso or 'unknown'}",
    ]
    if video_mode:
        lines.append(
            "Caption (secondary reference only — analyze VIDEO FRAMES for hook/cuts): "
            + (caption or "none")
        )
    else:
        lines.append(f"Caption:\n{caption}")
    lines.append(f"Hashtags: {', '.join(meta.hashtags[:25]) if meta.hashtags else 'none'}")
    if benchmark:
        lines.extend(
            [
                "",
                f"Page benchmark (@{meta.username}, last {benchmark['sample_size']} posts):",
                f"- Avg likes: {benchmark['avg_likes']}",
                f"- Avg comments: {benchmark['avg_comments']}",
                f"- Avg views: {benchmark['avg_views']}",
                f"Current post likes vs avg: {meta.likes} vs {benchmark['avg_likes']}",
            ]
        )
    return "\n".join(line for line in lines if line is not None)


async def analyze_cached_post(
    cached: CachedPost,
    *,
    telegram_id: int,
    lang: str,
    username: str | None = None,
) -> str:
    ok, reason = await check_ai_access(telegram_id, username)
    if not ok:
        raise ValueError(reason)

    item = cached.apify_item
    meta = post_meta_from_apify(item, cached.source_url)
    is_video = _is_video_item(item, cached.variants)
    benchmark = await _page_benchmark(
        meta.username,
        exclude_code=meta.short_code,
    )
    metrics = _build_metrics_text(
        item, cached.source_url, benchmark, video_mode=is_video
    )

    frames: list[tuple[str, str, str]] = []
    if settings.ai_vision_enabled and is_video:
        frames = await extract_vision_frames(item, cached.variants)

    image_b64 = None
    image_mime = "image/jpeg"
    if not frames and settings.ai_vision_enabled:
        preview = preview_image_url(item, cached.variants)
        if preview:
            img = await _download_image_b64(preview)
            if img:
                image_b64, image_mime = img

    report = await ai_client.analyze_post(
        metrics_text=metrics,
        lang=lang,
        frames=frames or None,
        image_b64=image_b64,
        image_mime=image_mime,
        is_video=is_video and bool(frames),
    )

    await log_activity(
        telegram_id,
        "ai_analysis",
        detail=cached.source_url[:200],
        meta={
            "short_code": meta.short_code,
            "vision": bool(frames or image_b64),
            "video_frames": len(frames),
            "ffmpeg": ffmpeg_ready(),
            "benchmark": bool(benchmark),
        },
    )
    return report
