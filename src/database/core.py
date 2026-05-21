import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from database.models.base import Base
import database.models  # noqa: F401


def _db_path() -> str:
    db_path = settings.APP_DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


engine = create_async_engine(f"sqlite+aiosqlite:///{_db_path()}", echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)