"""
Database session management utilities for the vet-core package.

This module provides async session factory, session management, and
transaction utilities for database operations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import text

from ..exceptions import DatabaseException, TransactionException

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages database sessions and provides transaction utilities.
    """

    def __init__(self, engine: AsyncEngine):
        """
        Initialize session manager with database engine.

        Args:
            engine: SQLAlchemy async engine
        """
        self.engine = engine
        self.session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

    async def create_session(self) -> AsyncSession:
        """
        Create a new database session.

        Returns:
            New async database session
        """
        return self.session_factory()

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

    async def execute_in_transaction(self, operation, *args, **kwargs):
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

    async def health_check(self) -> bool:
        """
        Check if database sessions can be created and used.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Session health check failed: {e}")
            return False


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


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Convenience function to get a database session.

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
    Convenience function to get a database transaction.

    Yields:
        Database session within a transaction

    Raises:
        RuntimeError: If session manager is not initialized
    """
    manager = get_session_manager()
    async with manager.get_transaction() as session:
        yield session


# Create session factory type for type hints
AsyncSessionLocal = async_sessionmaker[AsyncSession]
