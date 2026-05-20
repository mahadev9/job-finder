import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.database.models.base import Base


def _make_engine():
    db_path = settings.APP_DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)


engine = _make_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
