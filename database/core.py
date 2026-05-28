import logging
import os

import aiofiles.os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import database.models  # noqa: F401
from core.config import settings
from database.models.base import Base

logger = logging.getLogger("job-finder")


engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.APP_DATABASE_PATH}", echo=False
)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)

_ENSURE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_jobs_created_at ON jobs (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_matched_jobs_created_at ON matched_jobs (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_matched_jobs_status_created_at ON matched_jobs (status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_matched_jobs_score_desc ON matched_jobs (score)",
    "CREATE INDEX IF NOT EXISTS ix_token_usage_created_at ON token_usage (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_token_usage_pipeline ON token_usage (pipeline)",
]

_MIGRATIONS = [
    "ALTER TABLE jobs ADD COLUMN pipeline_ran BOOLEAN NOT NULL DEFAULT 0",
    "ALTER TABLE matched_jobs ADD COLUMN status_changed_at DATETIME",
    "ALTER TABLE token_usage ADD COLUMN reasoning_tokens INTEGER NOT NULL DEFAULT 0",
]


async def init_db() -> None:
    await aiofiles.os.makedirs(
        os.path.dirname(settings.APP_DATABASE_PATH), exist_ok=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _ENSURE_INDEXES:
            await conn.execute(text(stmt))
        for stmt in _MIGRATIONS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists
        logger.debug("Database indexes verified")
