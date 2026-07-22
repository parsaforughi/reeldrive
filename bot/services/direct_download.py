"""Direct download: Apify for links, HikerAPI fallback."""

from bot.services.apify import apify_downloader
from bot.services.hikerapi import hiker_client
from bot.services.instagram import MediaResult, instagram_downloader


def direct_download_ready() -> bool:
    return apify_downloader.ready or hiker_client.ready


async def download_media_url(url: str) -> MediaResult:
    if apify_downloader.ready:
        return await apify_downloader.download_media_url(url)
    if hiker_client.ready:
        return await instagram_downloader.download_media_url(url)
    raise ValueError(
        "دانلودر آماده نیست. APIFY_TOKEN یا HIKERAPI_KEY را در Railway تنظیم کن.\n"
        "Downloader not ready. Set APIFY_TOKEN or HIKERAPI_KEY."
    )
