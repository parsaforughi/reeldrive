"""Direct download: Apify for links; instagrapi fallback for legacy."""

import asyncio

from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool
from bot.services.instagram import MediaResult, instagram_downloader


def direct_download_ready() -> bool:
    return apify_downloader.ready or client_pool.service_ready


async def download_media_url(url: str) -> MediaResult:
    if apify_downloader.ready:
        return await apify_downloader.download_media_url(url)
    if client_pool.service_ready:
        return await asyncio.to_thread(
            instagram_downloader.download_media_url, url
        )
    raise ValueError(
        "دانلودر آماده نیست. APIFY_TOKEN را در Railway تنظیم کن.\n"
        "Downloader not ready. Set APIFY_TOKEN."
    )
