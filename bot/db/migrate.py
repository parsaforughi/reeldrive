"""One-time copy from legacy SQLite volume file into Postgres (empty DB only)."""

import logging
import sqlite3
from datetime import datetime

from sqlalchemy import func, select

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import ActivityLog, BotUser, UserConnection, WatchlistEntry

logger = logging.getLogger(__name__)


def _sqlite_path():
    for path in (settings.legacy_sqlite_path, settings.persistent_data_dir / "reeldrive.db"):
        if path.is_file() and path.stat().st_size > 512:
            return path
    return None


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def maybe_migrate_sqlite_to_postgres() -> None:
    if not settings.database_is_postgres:
        return

    sqlite_path = _sqlite_path()
    if not sqlite_path:
        return

    async with async_session() as session:
        existing = await session.scalar(select(func.count()).select_from(UserConnection))
        if existing and existing > 0:
            return

    logger.info("Postgres empty — importing from %s", sqlite_path)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        async with async_session() as session:
            for row in conn.execute("SELECT * FROM bot_users"):
                r = dict(row)
                session.add(
                    BotUser(
                        telegram_id=r["telegram_id"],
                        username=r.get("username"),
                        first_name=r.get("first_name"),
                        last_name=r.get("last_name"),
                        subscription_plan=r.get("subscription_plan") or "free",
                        subscription_expires_at=_parse_dt(r.get("subscription_expires_at")),
                        download_count=r.get("download_count") or 0,
                        command_count=r.get("command_count") or 0,
                        is_blocked=bool(r.get("is_blocked")),
                        language=r.get("language") or "",
                    )
                )
            for row in conn.execute("SELECT * FROM user_connections"):
                r = dict(row)
                session.add(
                    UserConnection(
                        telegram_id=r["telegram_id"],
                        instagram_username=r["instagram_username"],
                        instagram_user_id=r.get("instagram_user_id"),
                        status=r.get("status") or "pending",
                        verification_code=r.get("verification_code"),
                        code_expires_at=_parse_dt(r.get("code_expires_at")),
                        connected_at=_parse_dt(r.get("connected_at")),
                        last_bridge_message_id=r.get("last_bridge_message_id"),
                    )
                )
            try:
                for row in conn.execute("SELECT * FROM activity_logs"):
                    r = dict(row)
                    session.add(
                        ActivityLog(
                            telegram_id=r.get("telegram_id"),
                            event_type=r["event_type"],
                            detail=r.get("detail"),
                            meta_json=r.get("meta_json"),
                        )
                    )
            except sqlite3.OperationalError:
                pass
            await session.commit()
        logger.info("SQLite → Postgres migration completed")
    except Exception:
        logger.exception("SQLite migration failed")
    finally:
        conn.close()
