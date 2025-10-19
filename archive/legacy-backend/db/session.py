"""Database session management for the RCA backend."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

DATABASE_URL = settings.database.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Initialize the database connection by performing a simple health check."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_db() -> None:
    """Dispose of the database engine and release all pooled connections."""
    await engine.dispose()
