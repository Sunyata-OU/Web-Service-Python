"""
Enhanced async database layer with connection management and performance optimizations.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from src.config import get_settings
from src.logger import logger

# Get settings
settings = get_settings()

# Sync engine (for migrations and legacy compatibility)
sync_engine = create_engine(
    settings.database_url,
    poolclass=pool.QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    echo=settings.debug,
)

# Sync session
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Async engine with optimized connection pool
async_engine = create_async_engine(
    settings.async_database_url,
    pool_size=20,          # Core connection pool size
    max_overflow=30,       # Additional overflow connections
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections every hour
    pool_timeout=30,       # Timeout for getting connection
    echo=settings.debug,   # Log SQL in debug mode
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Declarative base
Base = declarative_base()


class DatabaseManager:
    """Database connection manager with health monitoring."""
    
    def __init__(self):
        self.async_engine = async_engine
        self.sync_engine = sync_engine
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def startup(self):
        """Initialize database connections and start monitoring."""
        try:
            # Test async connection
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
            logger.info("✅ Async database connection established")
            
            # Start health check monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())
            
        except Exception as e:
            logger.error(f"❌ Database startup failed: {e}")
            raise
    
    async def shutdown(self):
        """Clean shutdown of database connections."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("🛑 Database connections closed")
    
    async def _health_monitor(self):
        """Monitor database connection health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Test connection health
                async with AsyncSessionLocal() as session:
                    await session.execute("SELECT 1")
                
                logger.debug("🏥 Database health check: OK")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"🏥 Database health check failed: {e}")
    
    async def get_connection_stats(self) -> dict:
        """Get current connection pool statistics."""
        pool = async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }


# Global database manager instance
db_manager = DatabaseManager()


# Dependency injection functions
def get_sync_db() -> Session:
    """Get synchronous database session (for migrations, etc.)."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with explicit transaction management."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


# Database utilities
async def execute_raw_query(query: str, params: dict = None) -> list:
    """Execute raw SQL query safely."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params or {})
        return result.fetchall()


async def check_database_health() -> dict:
    """Check database health and return status."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute("SELECT version(), now()")
            row = result.fetchone()
            
            stats = await db_manager.get_connection_stats()
            
            return {
                "status": "healthy",
                "database_version": row[0] if row else "unknown",
                "server_time": row[1].isoformat() if row else None,
                "connection_stats": stats,
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_stats": await db_manager.get_connection_stats(),
        }