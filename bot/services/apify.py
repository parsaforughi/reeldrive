"""Instagram direct download via Apify Instagram Scraper actor."""

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from bot.config import settings
from bot.services.instagram import MediaResult

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
        media_urls = self._extract_media_urls(item)
        if not media_urls:
            raise ValueError("لینک مدیا در خروجی نبود / No media URLs in response")

        folder = TMP
        folder.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        async with aiohttp.ClientSession() as session:
            for i, media_url in enumerate(media_urls[:20]):
                path = await self._download_file(session, media_url, folder, i)
                if path:
                    paths.append(path)

        if not paths:
            raise ValueError("دانلود فایل ناموفق / File download failed")

        caption = (
            item.get("caption")
            or item.get("text")
            or item.get("alt")
            or ""
        )
        return MediaResult(
            paths=paths,
            caption=str(caption)[:1024],
            media_type=item.get("type") or results_type,
            direct_urls=media_urls[:10],
        )

    async def _run_actor(self, payload: dict) -> list[dict]:
        timeout = aiohttp.ClientTimeout(total=settings.apify_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self._run_url,
                params={"token": settings.apify_token},
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Apify HTTP %s: %s", resp.status, body[:500])
                    raise ValueError(
                        f"Apify خطا ({resp.status}). توکن یا اعتبار را چک کن."
                    )
                data = await resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "error" in data:
                    raise ValueError(str(data["error"]))
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

    def _extract_media_urls(self, item: dict) -> list[str]:
        urls: list[str] = []

        def add(u: str | None) -> None:
            if u and isinstance(u, str) and u.startswith("http"):
                urls.append(u)

        add(item.get("videoUrl"))
        add(item.get("video_url"))
        add(item.get("displayUrl"))
        add(item.get("display_url"))
        add(item.get("profilePicUrl"))
        add(item.get("profilePicUrlHD"))

        for key in ("images", "imageUrls", "carouselMedia", "latestPosts"):
            val = item.get(key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, str):
                        add(entry)
                    elif isinstance(entry, dict):
                        urls.extend(self._extract_media_urls(entry))

        for child in item.get("childPosts") or item.get("sidecarChildren") or []:
            if isinstance(child, dict):
                urls.extend(self._extract_media_urls(child))

        seen: set[str] = set()
        out: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    async def _download_file(
        self,
        session: aiohttp.ClientSession,
        url: str,
        folder: Path,
        index: int,
    ) -> Path | None:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                ext = ".mp4" if "video" in (resp.content_type or "") else ".jpg"
                if ".mp4" in url.split("?")[0].lower():
                    ext = ".mp4"
                path = folder / f"apify_{index}{ext}"
                path.write_bytes(data)
                return path
        except Exception:
            logger.exception("Failed to download %s", url[:80])
            return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        parsed = urlparse(url)
        return f"https://www.instagram.com{parsed.path}".rstrip("/") + "/"


apify_downloader = ApifyDownloader()
