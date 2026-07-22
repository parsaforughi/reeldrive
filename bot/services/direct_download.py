"""Direct Instagram media download through HikerAPI."""

from bot.services.hikerapi import hiker_client
from bot.services.instagram import MediaResult, instagram_downloader


def direct_download_ready() -> bool:
    return hiker_client.ready


async def download_media_url(url: str) -> MediaResult:
    if hiker_client.ready:
        return await instagram_downloader.download_media_url(url)
    raise ValueError(
        "دانلودر آماده نیست. HIKERAPI_KEY را در Railway تنظیم کن.\n"
        "Downloader not ready. Set HIKERAPI_KEY."
    )
