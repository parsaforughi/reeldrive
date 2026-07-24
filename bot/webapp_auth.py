"""Validate Telegram WebApp initData."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from bot.config import settings


def validate_init_data(
    init_data: str, *, max_age_seconds: int | None = None
) -> dict | None:
    """Return parsed user payload if initData is authentic, else None."""
    if not init_data:
        return None

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode(),
        hashlib.sha256,
    ).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None

    if max_age_seconds is not None:
        try:
            auth_date = int(pairs.get("auth_date", "0"))
        except ValueError:
            return None
        age = int(time.time()) - auth_date
        if auth_date <= 0 or age < -30 or age > max_age_seconds:
            return None

    user_raw = pairs.get("user")
    if not user_raw:
        return None
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(user, dict) or "id" not in user:
        return None
    return user
