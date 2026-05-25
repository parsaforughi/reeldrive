from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings
from bot.db.models import Base

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_language_column(conn) -> None:
    from sqlalchemy import text

    dialect = conn.dialect.name
    if dialect == "sqlite":
        sql = "ALTER TABLE bot_users ADD COLUMN language VARCHAR(5) DEFAULT ''"
    else:
        sql = "ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT ''"
    try:
        await conn.execute(text(sql))
    except Exception:
        pass


async def init_db() -> None:
    if settings.database_url.startswith("sqlite"):
        path = settings.database_url.split("///")[-1]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_language_column(conn)
