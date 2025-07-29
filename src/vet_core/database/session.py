"""
Database session management utilities for the vet-core package.

This module provides async session factory, session management, and
transaction utilities for database operations.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional

from sqlalchemy import MetaData, text
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import Pool

from ..exceptions import DatabaseException, TransactionException

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages database sessions and provides transaction utilities."""

    def __init__(
        self, engine: AsyncEngine, session_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize session manager with database engine.

        Args:
            engine: SQLAlchemy async engine
            session_config: Optional session configuration overrides
        """
        self.engine = engine
        self._is_initialized = False
        self._health_check_interval = 30.0  # seconds
        self._last_health_check = 0.0

        # Default session configuration
        default_config = {
            "expire_on_commit": False,
            "autoflush": True,
            "autocommit": False,
        }

        # Merge with provided config
        if session_config:
            default_config.update(session_config)

        self.session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=default_config.get("autoflush", False),
            expire_on_commit=default_config.get("expire_on_commit", False),
        )

    async def create_session(self) -> AsyncSession:
        """
        Create a new database session.

        Returns:
            New async database session
        """
        session = self.session_factory()
        return session

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions with automatic cleanup.

        Yields:
            Database session

        Example:
            async with session_manager.get_session() as session:
                # Use session for database operations
                result = await session.execute(select(User))
        """
        session = await self.create_session()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error, rolling back: {e}")
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database transactions with automatic commit/rollback.

        Yields:
            Database session within a transaction

        Example:
            async with session_manager.get_transaction() as session:
                # All operations in this block are part of one transaction
                user = User(name="John")
                session.add(user)
                # Transaction is automatically committed on success
        """
        async with self.get_session() as session:
            async with session.begin():
                try:
                    yield session
                except Exception as e:
                    logger.error(f"Transaction error, rolling back: {e}")
                    raise

    async def execute_in_transaction(
        self, operation: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute an operation within a transaction.

        Args:
            operation: Async function to execute
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            Result of the operation

        Raises:
            TransactionException: If database transaction fails
        """
        async with self.get_transaction() as session:
            try:
                return await operation(session, *args, **kwargs)
            except SQLAlchemyError as e:
                logger.error(f"Database operation failed: {e}")
                raise TransactionException(
                    "Database transaction failed",
                    operation=(
                        operation.__name__
                        if hasattr(operation, "__name__")
                        else str(operation)
                    ),
                    original_error=e,
                )
            except Exception as e:
                logger.error(f"Unexpected error in transaction: {e}")
                raise TransactionException(
                    "Unexpected error in transaction",
                    operation=(
                        operation.__name__
                        if hasattr(operation, "__name__")
                        else str(operation)
                    ),
                    original_error=e,
                )

    async def health_check(self, force: bool = False) -> Dict[str, Any]:
        """
        Comprehensive health check for database sessions and connections.

        Args:
            force: Force health check even if recently performed

        Returns:
            Dictionary with health check results
        """
        current_time = time.time()

        # Skip if recently checked (unless forced)
        if (
            not force
            and (current_time - self._last_health_check) < self._health_check_interval
        ):
            return {"status": "skipped", "reason": "recently_checked"}

        health_status: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": current_time,
            "checks": {},
            "pool_info": {},
        }

        try:
            # Verify basic session creation and query
            start_time = time.time()
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            query_time = time.time() - start_time

            health_status["checks"]["basic_query"] = {
                "status": "pass",
                "response_time": round(query_time * 1000, 2),  # ms
            }

            # Verify transaction capability
            start_time = time.time()
            async with self.get_transaction() as session:
                await session.execute(text("SELECT 1"))
            transaction_time = time.time() - start_time

            health_status["checks"]["transaction"] = {
                "status": "pass",
                "response_time": round(transaction_time * 1000, 2),  # ms
            }

            # Get pool information
            pool = self.engine.pool
            if hasattr(pool, "size"):
                health_status["pool_info"] = {
                    "size": pool.size(),
                    "checked_in": getattr(pool, "checkedin", lambda: 0)(),
                    "checked_out": getattr(pool, "checkedout", lambda: 0)(),
                    "overflow": getattr(pool, "overflow", lambda: 0)(),
                    "invalid": getattr(pool, "invalid", lambda: 0)(),
                }

            self._last_health_check = current_time

        except OperationalError as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["connection"] = {
                "status": "fail",
                "error": str(e),
                "error_type": "OperationalError",
            }
            logger.error(f"Database operational error during health check: {e}")

        except SQLAlchemyError as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = {
                "status": "fail",
                "error": str(e),
                "error_type": "SQLAlchemyError",
            }
            logger.error(f"Database error during health check: {e}")

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["general"] = {
                "status": "fail",
                "error": str(e),
                "error_type": type(e).__name__,
            }
            logger.error(f"Unexpected error during health check: {e}")

        return health_status

    async def initialize_database(self, metadata: Optional[MetaData] = None) -> bool:
        """
        Initialize database schema and perform setup operations.

        Args:
            metadata: SQLAlchemy metadata object containing table definitions

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Starting database initialization...")

            # Verify connection first
            health = await self.health_check(force=True)
            if health["status"] != "healthy":
                logger.error("Database health check failed during initialization")
                return False

            # Create tables if metadata provided
            if metadata:
                async with self.engine.begin() as conn:
                    await conn.run_sync(metadata.create_all)
                logger.info("Database tables created successfully")

            # Perform any additional initialization
            async with self.get_session() as session:
                # Verify that we can perform basic operations
                await session.execute(text("SELECT version()"))
                logger.info("Database initialization completed successfully")

            self._is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    async def cleanup_database(
        self, metadata: Optional[MetaData] = None, drop_all: bool = False
    ) -> bool:
        """
        Clean up database resources and optionally drop schema.

        Args:
            metadata: SQLAlchemy metadata object containing table definitions
            drop_all: Whether to drop all tables (use with caution)

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info("Starting database cleanup...")

            if drop_all and metadata:
                async with self.engine.begin() as conn:
                    await conn.run_sync(metadata.drop_all)
                logger.warning("All database tables dropped")

            # Close all sessions and connections
            await self.close_all_sessions()

            logger.info("Database cleanup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            return False

    async def close_all_sessions(self) -> None:
        """Close all active sessions and dispose of the engine."""
        try:
            # Dispose of the engine (closes all connections)
            await self.engine.dispose()
            logger.info("All database sessions and connections closed")
        except Exception as e:
            logger.error(f"Error closing database sessions: {e}")

    async def execute_with_retry(
        self,
        operation: Callable[[AsyncSession], Awaitable[Any]],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ) -> Any:
        """
        Execute a database operation with retry logic for transient failures.

        Args:
            operation: Async function that takes a session and returns a result
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            exponential_backoff: Whether to use exponential backoff

        Returns:
            Result of the operation

        Raises:
            DatabaseException: If operation fails after all retries
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                async with self.get_transaction() as session:
                    return await operation(session)

            except (DisconnectionError, OperationalError) as e:
                last_exception = e
                if attempt < max_retries:
                    delay = retry_delay * (2**attempt if exponential_backoff else 1)
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Database operation failed after {max_retries + 1} attempts: {e}"
                    )

            except Exception as e:
                # Don't retry for non-transient errors
                logger.error(f"Non-retryable database operation error: {e}")
                raise DatabaseException(
                    "Database operation failed",
                    details={
                        "operation": (
                            operation.__name__
                            if hasattr(operation, "__name__")
                            else str(operation)
                        )
                    },
                    original_error=e,
                )

        # If we get here, all retries failed
        raise DatabaseException(
            f"Database operation failed after {max_retries + 1} attempts",
            details={
                "operation": (
                    operation.__name__
                    if hasattr(operation, "__name__")
                    else str(operation)
                ),
                "max_retries": max_retries,
            },
            original_error=last_exception,
        )

    @property
    def is_initialized(self) -> bool:
        """Check if the database has been initialized."""
        return self._is_initialized

    async def get_pool_status(self) -> Dict[str, Any]:
        """
        Get detailed connection pool status information.

        Returns:
            Dictionary with pool status information
        """
        pool = self.engine.pool

        # Safely mask password in URL
        url_str = str(self.engine.url)
        if hasattr(self.engine.url, "password") and self.engine.url.password:
            url_str = url_str.replace(str(self.engine.url.password), "***")

        status = {
            "pool_class": pool.__class__.__name__,
            "url": url_str,
        }

        if hasattr(pool, "size"):
            status.update(
                {
                    "size": str(pool.size()),
                    "checked_in": str(getattr(pool, "checkedin", lambda: 0)()),
                    "checked_out": str(getattr(pool, "checkedout", lambda: 0)()),
                    "overflow": str(getattr(pool, "overflow", lambda: 0)()),
                    "invalid": str(getattr(pool, "invalid", lambda: 0)()),
                }
            )

        return status


# Global session manager instance (will be initialized by application)
_session_manager: Optional[SessionManager] = None


def initialize_session_manager(engine: AsyncEngine) -> SessionManager:
    """
    Initialize the global session manager.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        Initialized session manager
    """
    global _session_manager
    _session_manager = SessionManager(engine)
    logger.info("Session manager initialized")
    return _session_manager


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    Returns:
        Session manager instance

    Raises:
        RuntimeError: If session manager is not initialized
    """
    if _session_manager is None:
        raise RuntimeError(
            "Session manager not initialized. Call initialize_session_manager() first."
        )
    return _session_manager


def get_engine() -> AsyncEngine:
    """
    Get the database engine from the global session manager.

    Returns:
        SQLAlchemy async engine

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    return manager.engine


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.

    Yields:
        Database session

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    async with manager.get_session() as session:
        yield session


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database transaction.

    Yields:
        Database session within a transaction

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    async with manager.get_transaction() as session:
        yield session


async def execute_with_retry(
    operation: Callable[[AsyncSession], Awaitable[Any]],
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
) -> Any:
    """
    Execute database operations with retry logic.

    Args:
        operation: Async function that takes a session and returns a result
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff

    Returns:
        Result of the operation

    Raises:
        RuntimeError: If session manager is not initialized
        DatabaseException: If operation fails after all retries
    """
    manager = get_session_manager()
    return await manager.execute_with_retry(
        operation, max_retries, retry_delay, exponential_backoff
    )


async def health_check(force: bool = False) -> Dict[str, Any]:
    """
    Perform database health check.

    Args:
        force: Force health check even if recently performed

    Returns:
        Dictionary with health check results

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    return await manager.health_check(force)


async def initialize_database(metadata: Optional[MetaData] = None) -> bool:
    """
    Initialize database.

    Args:
        metadata: SQLAlchemy metadata object containing table definitions

    Returns:
        True if initialization successful, False otherwise

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    return await manager.initialize_database(metadata)


async def cleanup_database(
    metadata: Optional[MetaData] = None, drop_all: bool = False
) -> bool:
    """
    Clean up database.

    Args:
        metadata: SQLAlchemy metadata object containing table definitions
        drop_all: Whether to drop all tables (use with caution)

    Returns:
        True if cleanup successful, False otherwise

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    return await manager.cleanup_database(metadata, drop_all)


async def get_pool_status() -> Dict[str, Any]:
    """
    Get connection pool status.

    Returns:
        Dictionary with pool status information

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    return await manager.get_pool_status()


# Create session factory type for type hints
AsyncSessionLocal = async_sessionmaker[AsyncSession]
