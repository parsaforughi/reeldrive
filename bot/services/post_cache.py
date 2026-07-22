"""In-memory cache of downloaded posts for callback actions."""

from dataclasses import dataclass, field

from bot.media_variants import MediaVariant

_MAX = 500


@dataclass
class CachedPost:
    source_url: str
    source_item: dict = field(default_factory=dict)
    direct_urls: list[str] = field(default_factory=list)
    variants: list[MediaVariant] = field(default_factory=list)


_cache: dict[str, CachedPost] = {}


def cache_post(short_code: str, entry: CachedPost) -> None:
    if not short_code:
        return
    if len(_cache) >= _MAX:
        for key in list(_cache.keys())[: _MAX // 4]:
            _cache.pop(key, None)
    _cache[short_code] = entry


def get_post(short_code: str) -> CachedPost | None:
    return _cache.get(short_code)
