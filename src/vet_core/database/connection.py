"""
Database connection utilities for the vet-core package.

This module provides async SQLAlchemy engine configuration and connection
management utilities for PostgreSQL databases.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, QueuePool

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
            if not parsed.scheme.startswith("postgresql"):
                raise ValueError(
                    "Database URL must use postgresql:// or postgresql+asyncpg://"
                )
            if not parsed.hostname:
                raise ValueError("Database URL must include hostname")
            if not parsed.path or parsed.path == "/":
                raise ValueError("Database URL must include database name")
        except Exception as e:
            raise ValueError(f"Invalid database URL: {e}")

    def get_async_url(self) -> str:
        """Convert database URL to async format if needed."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self.database_url


def create_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    pool_reset_on_return: str = "commit",
    pool_pre_ping: bool = True,
    echo: bool = False,
    echo_pool: bool = False,
    use_null_pool: bool = False,
    connect_args: Optional[dict] = None,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine with proper configuration.

    Args:
        database_url: PostgreSQL connection URL
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum number of connections that can overflow the pool
        pool_timeout: Timeout for getting connection from pool
        pool_recycle: Time in seconds to recycle connections
        pool_reset_on_return: How to reset connections when returned to pool
        pool_pre_ping: Whether to validate connections before use
        echo: Whether to echo SQL statements
        echo_pool: Whether to echo pool events
        use_null_pool: Whether to use NullPool (useful for testing)
        connect_args: Additional connection arguments

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
    engine_kwargs: Dict[str, Any] = {
        "echo": config.echo,
        "echo_pool": config.echo_pool,
        "future": True,
    }

    # Add connection arguments if provided
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    # Pool configuration
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        # Use AsyncAdaptedQueuePool for async engines
        engine_kwargs.update(
            {
                "poolclass": AsyncAdaptedQueuePool,
                "pool_size": config.pool_size,
                "max_overflow": config.max_overflow,
                "pool_timeout": config.pool_timeout,
                "pool_recycle": config.pool_recycle,
                "pool_pre_ping": pool_pre_ping,
                "pool_reset_on_return": pool_reset_on_return,
            }
        )

    try:
        engine = create_async_engine(async_url, **engine_kwargs)
        logger.info(f"Created async database engine for {urlparse(async_url).hostname}")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


async def test_connection(
    engine: AsyncEngine, max_retries: int = 3, retry_delay: float = 1.0
) -> bool:
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
                logger.warning(
                    f"Database connection test failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                await asyncio.sleep(retry_delay * (2**attempt))  # Exponential backoff
            else:
                logger.error(
                    f"Database connection test failed after {max_retries + 1} attempts: {e}"
                )
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
    engine: AsyncEngine, timeout: float = 30.0, check_interval: float = 1.0
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
        original_error=None,
    )


async def check_database_exists(engine: AsyncEngine, database_name: str) -> bool:
    """
    Check if a database exists.

    Args:
        engine: SQLAlchemy async engine
        database_name: Name of the database to check

    Returns:
        True if database exists, False otherwise
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": database_name},
            )
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if database exists: {e}")
        return False


async def get_database_info(engine: AsyncEngine) -> dict:
    """
    Get comprehensive database information.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        Dictionary with database information
    """
    info = {}

    try:
        async with engine.begin() as conn:
            # Get PostgreSQL version
            version_result = await conn.execute(text("SELECT version()"))
            info["version"] = version_result.scalar()

            # Get current database name
            db_result = await conn.execute(text("SELECT current_database()"))
            info["database"] = db_result.scalar()

            # Get current user
            user_result = await conn.execute(text("SELECT current_user"))
            info["user"] = user_result.scalar()

            # Get server encoding
            encoding_result = await conn.execute(text("SHOW server_encoding"))
            info["encoding"] = encoding_result.scalar()

            # Get timezone
            tz_result = await conn.execute(text("SHOW timezone"))
            info["timezone"] = tz_result.scalar()

            # Get connection count
            conn_result = await conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                )
            )
            info["active_connections"] = conn_result.scalar()

    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        info["error"] = str(e)

    return info


async def create_database_if_not_exists(
    admin_engine: AsyncEngine, database_name: str, owner: Optional[str] = None
) -> bool:
    """
    Create a database if it doesn't exist.

    Args:
        admin_engine: SQLAlchemy engine with admin privileges
        database_name: Name of the database to create
        owner: Optional owner for the database

    Returns:
        True if database was created or already exists, False on error
    """
    try:
        # Check if database already exists
        if await check_database_exists(admin_engine, database_name):
            logger.info(f"Database '{database_name}' already exists")
            return True

        # Create database
        async with admin_engine.begin() as conn:
            # Use autocommit mode for CREATE DATABASE
            await conn.execute(text("COMMIT"))

            create_sql = f'CREATE DATABASE "{database_name}"'
            if owner:
                create_sql += f' OWNER "{owner}"'

            await conn.execute(text(create_sql))
            logger.info(f"Database '{database_name}' created successfully")
            return True

    except Exception as e:
        logger.error(f"Error creating database '{database_name}': {e}")
        return False


def get_database_url(
    host: str,
    port: int = 5432,
    database: str = "postgres",
    username: str = "postgres",
    password: str = "",  # nosec B107
    driver: str = "asyncpg",
    **kwargs: Any,
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
        **kwargs: Additional URL parameters

    Returns:
        Formatted database URL
    """
    if password:
        auth = f"{username}:{password}"
    else:
        auth = username

    base_url = f"postgresql+{driver}://{auth}@{host}:{port}/{database}"

    # Add additional parameters if provided
    if kwargs:
        params = "&".join(f"{k}={v}" for k, v in kwargs.items())
        base_url += f"?{params}"

    return base_url
