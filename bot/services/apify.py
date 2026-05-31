"""Instagram direct download via Apify Instagram Scraper actor."""

import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from bot.config import settings
from bot.services.cdn_download import download_cdn_url
from bot.media_variants import extract_media_variants, pick_best_download
from bot.post_display import post_meta_from_apify
from bot.services.instagram import MediaResult
from bot.services.post_cache import CachedPost, cache_post

logger = logging.getLogger(__name__)

TMP = Path("/tmp/reeldrive")

PROFILE_PATH_RE = re.compile(
    r"instagram\.com/([a-zA-Z0-9._]+)/?$", re.IGNORECASE
)


class ApifyDownloader:
    @property
    def ready(self) -> bool:
        return bool(settings.apify_token)

    @property
    def _run_url(self) -> str:
        actor = settings.apify_actor.strip("/")
        return (
            f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
        )

    async def fetch_profile_item(self, username: str) -> dict:
        """Public profile metadata via Apify (no IG login)."""
        if not self.ready:
            raise ValueError("Apify not configured")

        handle = username.strip().lstrip("@").lower()
        url = f"https://www.instagram.com/{handle}/"
        payload = {
            "directUrls": [url],
            "resultsType": "details",
            "resultsLimit": 1,
        }
        items = await self._run_actor(payload)
        if not items:
            raise ValueError("Profile not found")
        return items[0]

    @staticmethod
    def profile_biography(item: dict) -> str:
        for key in ("biography", "bio", "Biography", "biographyText"):
            val = item.get(key)
            if val:
                return str(val)
        return ""

    @staticmethod
    def profile_user_id(item: dict) -> str:
        for key in ("id", "userId", "ownerId", "instagramId", "pk"):
            val = item.get(key)
            if val is not None:
                return str(val)
        return ""

    async def download_media_url(self, url: str) -> MediaResult:
        if not self.ready:
            raise ValueError("Apify تنظیم نشده / Apify not configured")

        normalized = self._normalize_url(url)
        results_type = self._results_type(normalized)
        payload = {
            "directUrls": [normalized],
            "resultsType": results_type,
            "resultsLimit": 1,
        }

        items = await self._run_actor(payload)
        if not items:
            raise ValueError("پست پیدا نشد / No data from Instagram")

        item = items[0]
        variants = extract_media_variants(item)
        if not variants:
            raise ValueError("لینک مدیا در خروجی نبود / No media URLs in response")

        best = pick_best_download(variants)
        all_urls = [v.url for v in variants]

        folder = TMP
        folder.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        async with aiohttp.ClientSession() as session:
            # Main preview: best quality video, or all carousel images
            if best and best.kind == "video":
                path = await download_cdn_url(session, best.url, folder, 0)
                if path:
                    paths.append(path)
            else:
                for i, var in enumerate(variants[:10]):
                    if var.kind == "image":
                        path = await download_cdn_url(session, var.url, folder, i)
                        if path:
                            paths.append(path)
            if not paths and best:
                path = await download_cdn_url(session, best.url, folder, 0)
                if path:
                    paths.append(path)

        if not paths:
            raise ValueError("دانلود فایل ناموفق / File download failed")

        meta = post_meta_from_apify(item, normalized)
        if meta.short_code:
            cache_post(
                meta.short_code,
                CachedPost(
                    source_url=normalized,
                    apify_item=item,
                    direct_urls=all_urls,
                    variants=variants,
                ),
            )
        return MediaResult(
            paths=paths,
            caption=meta.caption,
            media_type=item.get("type") or results_type,
            direct_urls=all_urls,
            post_meta=meta,
            source_url=normalized,
        )

    async def _run_actor(self, payload: dict) -> list[dict]:
        timeout = aiohttp.ClientTimeout(total=settings.apify_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self._run_url,
                params={"token": settings.apify_token},
                json=payload,
            ) as resp:
                body_text = await resp.text()
                # 200 OK and 201 Created are both success (Apify may return either)
                if not (200 <= resp.status < 300):
                    logger.error("Apify HTTP %s: %s", resp.status, body_text[:500])
                    raise ValueError(
                        f"Apify خطا ({resp.status}). توکن یا اعتبار را چک کن."
                    )
                if not body_text.strip():
                    return []
                try:
                    data = json.loads(body_text)
                except json.JSONDecodeError as exc:
                    raise ValueError("پاسخ Apify نامعتبر بود.") from exc
                return self._parse_dataset_response(data)

    def _parse_dataset_response(self, data: object) -> list[dict]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]

        if not isinstance(data, dict):
            return []

        if "error" in data:
            raise ValueError(str(data["error"]))

        # Accidental /runs response: { "data": { "id": "...", "status": "..." } }
        inner = data.get("data")
        if isinstance(inner, dict) and "id" in inner and "defaultDatasetId" in inner:
            raise ValueError(
                "Apify فقط Run را ساخت. از run-sync-get-dataset-items استفاده می‌شود — "
                "اگر باز هم این پیام را دیدی، Actor یا توکن را چک کن."
            )

        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]

        for key in ("items", "datasetItems"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]

        return []

    def _results_type(self, url: str) -> str:
        lower = url.lower()
        if "/reel/" in lower or "/reels/" in lower:
            return "reels"
        if "/p/" in lower or "/tv/" in lower:
            return "posts"
        if PROFILE_PATH_RE.search(lower):
            return "details"
        return "posts"

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        parsed = urlparse(url)
        return f"https://www.instagram.com{parsed.path}".rstrip("/") + "/"


apify_downloader = ApifyDownloader()
