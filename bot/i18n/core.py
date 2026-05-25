from typing import Literal

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import BotUser
from bot.i18n.strings import MESSAGES

Lang = Literal["fa", "en", "ar"]
SUPPORTED: tuple[Lang, ...] = ("fa", "en", "ar")
DEFAULT_LANG: Lang = "fa"

_lang_cache: dict[int, Lang] = {}


def normalize_lang(code: str | None) -> Lang | None:
    if not code:
        return None
    c = code.strip().lower()[:5]
    if c in SUPPORTED:
        return c  # type: ignore[return-value]
    return None


def t(key: str, lang: str, **kwargs) -> str:
    lang = normalize_lang(lang) or DEFAULT_LANG
    block = MESSAGES.get(key)
    if not block:
        return key
    text = block.get(lang) or block.get(DEFAULT_LANG) or key
    if kwargs:
        kwargs.setdefault("bridge", settings.bridge_ig_handle)
        kwargs.setdefault("name", settings.bot_name)
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


async def get_user_lang(telegram_id: int) -> Lang | None:
    if telegram_id in _lang_cache:
        cached = _lang_cache[telegram_id]
        return cached if cached else None

    async with async_session() as session:
        row = await session.get(BotUser, telegram_id)
        if not row or not row.language:
            return None
        lang = normalize_lang(row.language)
        if lang:
            _lang_cache[telegram_id] = lang
        return lang


async def require_user_lang(telegram_id: int) -> Lang:
    return (await get_user_lang(telegram_id)) or DEFAULT_LANG


async def set_user_lang(telegram_id: int, lang: str) -> Lang:
    chosen = normalize_lang(lang) or DEFAULT_LANG
    async with async_session() as session:
        row = await session.get(BotUser, telegram_id)
        if row:
            row.language = chosen
        else:
            session.add(BotUser(telegram_id=telegram_id, language=chosen))
        await session.commit()
    _lang_cache[telegram_id] = chosen
    return chosen


async def tu(telegram_id: int, key: str, **kwargs) -> str:
    lang = await require_user_lang(telegram_id)
    return t(key, lang, **kwargs)
