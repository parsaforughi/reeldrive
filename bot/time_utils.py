"""UTC storage helpers and ISO serialization for the dashboard."""

from datetime import datetime, timezone

from aiogram.types import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat() + "Z"


def user_display_label(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    name = (user.full_name or "").strip()
    if name:
        return f"{name} ({user.id})"
    return str(user.id)
