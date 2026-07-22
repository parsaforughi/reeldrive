"""Download Instagram CDN URLs returned by the data API or DM payload."""

import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

TMP = Path("/tmp/reeldrive")

IG_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.instagram.com/",
    "Accept": "*/*",
}


async def download_cdn_url(
    session: aiohttp.ClientSession,
    url: str,
    folder: Path,
    index: int,
    *,
    is_video: bool | None = None,
) -> Path | None:
    try:
        async with session.get(url, headers=IG_CDN_HEADERS) as resp:
            if not (200 <= resp.status < 300):
                logger.warning("CDN HTTP %s for %s", resp.status, url[:80])
                return None
            data = await resp.read()
            if not data:
                return None
            if is_video is True:
                ext = ".mp4"
            elif is_video is False:
                ext = ".jpg"
            else:
                ctype = (resp.content_type or "").lower()
                ext = ".mp4" if "video" in ctype else ".jpg"
                if ".mp4" in url.split("?")[0].lower():
                    ext = ".mp4"
            path = folder / f"cdn_{index}{ext}"
            path.write_bytes(data)
            return path
    except Exception:
        logger.exception("CDN download failed %s", url[:80])
        return None


async def download_cdn_files(
    files: list[tuple[str, bool]],
    folder: Path | None = None,
) -> list[Path]:
    """Download (cdn_url, is_video) pairs; returns local paths in order."""
    if not files:
        return []
    dest = folder or TMP
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    async with aiohttp.ClientSession() as session:
        for i, (url, is_video) in enumerate(files[:10]):
            path = await download_cdn_url(session, url, dest, i, is_video=is_video)
            if path:
                paths.append(path)
    return paths
