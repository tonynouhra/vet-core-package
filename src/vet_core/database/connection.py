"""
Database connection utilities for the vet-core package.

This module provides async SQLAlchemy engine configuration and connection
management utilities for PostgreSQL databases.
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse
import time

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..exceptions import ConnectionException, DatabaseException

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration class for database connections."""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        echo_pool: bool = False,
    ):
        """
        Initialize database configuration.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum number of connections that can overflow the pool
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time in seconds to recycle connections
            echo: Whether to echo SQL statements
            echo_pool: Whether to echo pool events
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.echo_pool = echo_pool
        
        # Validate URL
        self._validate_database_url()
    
    def _validate_database_url(self) -> None:
        """Validate the database URL format."""
        try:
            parsed = urlparse(self.database_url)
            if not parsed.scheme.startswith('postgresql'):
                raise ValueError("Database URL must use postgresql:// or postgresql+asyncpg://")
            if not parsed.hostname:
                raise ValueError("Database URL must include hostname")
            if not parsed.path or parsed.path == '/':
                raise ValueError("Database URL must include database name")
        except Exception as e:
            raise ValueError(f"Invalid database URL: {e}")
    
    def get_async_url(self) -> str:
        """Convert database URL to async format if needed."""
        if self.database_url.startswith('postgresql://'):
            return self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return self.database_url


def create_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False,
    echo_pool: bool = False,
    use_null_pool: bool = False,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine with proper configuration.
    
    Args:
        database_url: PostgreSQL connection URL
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum number of connections that can overflow the pool
        pool_timeout: Timeout for getting connection from pool
        pool_recycle: Time in seconds to recycle connections
        echo: Whether to echo SQL statements
        echo_pool: Whether to echo pool events
        use_null_pool: Whether to use NullPool (useful for testing)
        
    Returns:
        Configured async SQLAlchemy engine
        
    Raises:
        ValueError: If database URL is invalid
    """
    config = DatabaseConfig(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
        echo_pool=echo_pool,
    )
    
    async_url = config.get_async_url()
    
    # Engine configuration
    engine_kwargs = {
        "echo": config.echo,
        "echo_pool": config.echo_pool,
        "future": True,
    }
    
    # Pool configuration
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
            "pool_recycle": config.pool_recycle,
            "pool_pre_ping": True,  # Validate connections before use
        })
    
    try:
        engine = create_async_engine(async_url, **engine_kwargs)
        logger.info(f"Created async database engine for {urlparse(async_url).hostname}")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


async def test_connection(engine: AsyncEngine, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Test database connection health with retry logic.
    
    Args:
        engine: SQLAlchemy async engine
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        True if connection is healthy, False otherwise
    """
    for attempt in range(max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Database connection test failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"Database connection test failed after {max_retries + 1} attempts: {e}")
                return False
    return False


async def close_engine(engine: AsyncEngine) -> None:
    """
    Properly close the database engine and all connections.
    
    Args:
        engine: SQLAlchemy async engine to close
    """
    try:
        await engine.dispose()
        logger.info("Database engine closed successfully")
    except Exception as e:
        logger.error(f"Error closing database engine: {e}")


async def wait_for_database(
    engine: AsyncEngine, 
    timeout: float = 30.0, 
    check_interval: float = 1.0
) -> bool:
    """
    Wait for database to become available.
    
    Args:
        engine: SQLAlchemy async engine
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        True if database becomes available, False if timeout
        
    Raises:
        ConnectionException: If database doesn't become available within timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await test_connection(engine, max_retries=0):
            return True
        await asyncio.sleep(check_interval)
    
    raise ConnectionException(
        f"Database did not become available within {timeout} seconds",
        original_error=None
    )


def get_database_url(
    host: str,
    port: int = 5432,
    database: str = "postgres",
    username: str = "postgres",
    password: str = "",
    driver: str = "asyncpg",
) -> str:
    """
    Construct a PostgreSQL database URL.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        driver: Database driver (asyncpg for async)
        
    Returns:
        Formatted database URL
    """
    if password:
        auth = f"{username}:{password}"
    else:
        auth = username
    
    return f"postgresql+{driver}://{auth}@{host}:{port}/{database}"