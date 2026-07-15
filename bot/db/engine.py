import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings
from bot.db.models import Base

logger = logging.getLogger(__name__)

_engine_kwargs: dict = {}
if settings.database_is_postgres:
    _engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    }

engine = create_async_engine(settings.database_url, echo=False, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def sqlite_db_path() -> Path | None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        return None
    return Path(url.split("sqlite+aiosqlite:///")[-1])


async def _ensure_language_column(conn) -> None:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        sql = "ALTER TABLE bot_users ADD COLUMN language VARCHAR(5) DEFAULT ''"
    else:
        sql = "ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT ''"
    try:
        await conn.execute(text(sql))
    except Exception:
        pass


async def _ensure_renewal_reminder_column(conn) -> None:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        sql = "ALTER TABLE bot_users ADD COLUMN renewal_reminder_expiry DATETIME"
    else:
        sql = "ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS renewal_reminder_expiry TIMESTAMP"
    try:
        await conn.execute(text(sql))
    except Exception:
        pass


async def init_db() -> None:
    db_path = sqlite_db_path()
    if db_path:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("SQLite database file: %s", db_path)
    settings.persistent_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.persistent_data_dir / "sessions").mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_language_column(conn)
        await _ensure_renewal_reminder_column(conn)


async def db_ping() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database ping failed: %s", exc)
        return False
