"""
Database connection management for RCA Engine.
Provides async database connection pool and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy import event, text
from core.config import settings
from core.db.models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        """Initialize database manager."""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False
    
    def _create_engine(self) -> AsyncEngine:
        """Create async database engine with connection pooling."""
        engine = create_async_engine(
            settings.database.DATABASE_URL,
            pool_size=settings.database.DB_POOL_SIZE,
            max_overflow=settings.database.DB_MAX_OVERFLOW,
            pool_timeout=settings.database.DB_POOL_TIMEOUT,
            pool_recycle=settings.database.DB_POOL_RECYCLE,
            pool_pre_ping=settings.database.DB_POOL_PRE_PING,
            echo=settings.DEBUG,
            future=True,
        )
        
        # Register connection event listeners
        @event.listens_for(engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new database connections."""
            logger.debug("New database connection established")
        
        @event.listens_for(engine.sync_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """Handle database connection closures."""
            logger.debug("Database connection closed")
        
        return engine
    
    async def initialize(self):
        """Initialize database engine and session factory."""
        if self._initialized:
            logger.warning("Database manager already initialized")
            return
        
        try:
            logger.info("Initializing database connection pool...")
            self._engine = self._create_engine()
            
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self._initialized = True
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info("Creating database tables...")
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.warning("Dropping all database tables...")
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    async def close(self):
        """Close database connections and cleanup resources."""
        if not self._initialized:
            return
        
        try:
            logger.info("Closing database connections...")
            if self._engine:
                await self._engine.dispose()
            self._initialized = False
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            raise
    
    def get_session(self) -> AsyncSession:
        """
        Get a new database session.
        
        Returns:
            AsyncSession: New database session
            
        Raises:
            RuntimeError: If database manager is not initialized
        """
        if not self._initialized or not self._session_factory:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")
        
        return self._session_factory()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions with automatic cleanup.
        
        Usage:
            async with db_manager.session() as session:
                # Use session here
                pass
        
        Yields:
            AsyncSession: Database session
        """
        if not self._initialized:
            await self.initialize()
        
        session = self.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """
        Check database connection health.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        if not self._initialized:
            return False
        
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @property
    def is_initialized(self) -> bool:
        """Check if database manager is initialized."""
        return self._initialized
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if not self._engine:
            raise RuntimeError("Database manager not initialized")
        return self._engine


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.session() as session:
        yield session


def get_db_session() -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """
    Provide a callable compatible with legacy call-sites that expect to obtain an
    async context manager via ``async with get_db_session()():``.
    """
    return db_manager.session


async def init_db():
    """Initialize database and create tables."""
    await db_manager.initialize()
    await db_manager.create_tables()


async def close_db():
    """Close database connections."""
    await db_manager.close()


# Export commonly used items
__all__ = [
    "DatabaseManager",
    "db_manager",
    "get_db",
    "get_db_session",
    "init_db",
    "close_db",
]
