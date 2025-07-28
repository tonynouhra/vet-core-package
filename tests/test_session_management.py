"""
Tests for database session management functionality.

This module tests the enhanced session management features including
async session factory, transaction context managers, connection pooling,
health checks, and database initialization/cleanup utilities.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, text
from sqlalchemy.exc import DisconnectionError, OperationalError

from vet_core.database import (
    SessionManager,
    cleanup_database,
    create_engine,
    execute_with_retry,
    get_pool_status,
    get_session,
    get_session_manager,
    get_transaction,
    health_check,
    initialize_database,
    initialize_session_manager,
)
from vet_core.exceptions import DatabaseException, TransactionException


@pytest.fixture
async def mock_engine():
    """Create a mock async engine for testing."""
    engine = AsyncMock()
    engine.url = MagicMock()
    engine.url.password = "test_password"

    # Mock pool
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedin.return_value = 8
    pool.checkedout.return_value = 2
    pool.overflow.return_value = 0
    pool.invalid.return_value = 0
    pool.__class__.__name__ = "QueuePool"
    engine.pool = pool

    return engine


@pytest.fixture
async def session_manager(mock_engine):
    """Create a SessionManager instance for testing."""
    return SessionManager(mock_engine)


@pytest.fixture
def test_metadata():
    """Create test metadata with a simple table."""
    metadata = MetaData()
    test_table = Table(
        "test_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
    )
    return metadata


class TestSessionManager:
    """Test cases for SessionManager class."""

    async def test_session_manager_initialization(self, mock_engine):
        """Test SessionManager initialization."""
        manager = SessionManager(mock_engine)

        assert manager.engine == mock_engine
        assert not manager.is_initialized
        assert manager.session_factory is not None

    async def test_session_manager_with_custom_config(self, mock_engine):
        """Test SessionManager initialization with custom configuration."""
        custom_config = {
            "expire_on_commit": True,
            "autoflush": False,
        }

        manager = SessionManager(mock_engine, session_config=custom_config)
        assert manager.engine == mock_engine

    async def test_create_session(self, session_manager):
        """Test session creation."""
        mock_session = AsyncMock()

        with patch.object(
            session_manager, "session_factory", return_value=mock_session
        ) as mock_factory:
            session = await session_manager.create_session()
            assert session == mock_session
            mock_factory.assert_called_once()

    async def test_get_session_context_manager(self, session_manager):
        """Test session context manager."""
        mock_session = AsyncMock()

        with patch.object(session_manager, "create_session", return_value=mock_session):
            async with session_manager.get_session() as session:
                assert session == mock_session

            mock_session.close.assert_called_once()

    async def test_get_session_context_manager_with_exception(self, session_manager):
        """Test session context manager handles exceptions properly."""
        mock_session = AsyncMock()

        with patch.object(session_manager, "create_session", return_value=mock_session):
            with pytest.raises(ValueError):
                async with session_manager.get_session() as session:
                    raise ValueError("Test exception")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    async def test_get_transaction_context_manager(self, session_manager):
        """Test transaction context manager."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock

        mock_session = AsyncMock()
        mock_transaction = AsyncMock()

        # Create a proper async context manager mock
        @asynccontextmanager
        async def mock_begin():
            yield mock_transaction

        mock_session.begin = mock_begin

        with patch.object(session_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            async with session_manager.get_transaction() as session:
                assert session == mock_session

    async def test_execute_in_transaction_success(self, session_manager):
        """Test successful transaction execution."""
        mock_session = AsyncMock()
        expected_result = "test_result"

        async def test_operation(session, arg1, arg2=None):
            assert session == mock_session
            assert arg1 == "test_arg"
            assert arg2 == "test_kwarg"
            return expected_result

        with patch.object(session_manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            result = await session_manager.execute_in_transaction(
                test_operation, "test_arg", arg2="test_kwarg"
            )

            assert result == expected_result

    async def test_execute_in_transaction_failure(self, session_manager):
        """Test transaction execution with failure."""
        mock_session = AsyncMock()

        async def failing_operation(session):
            raise OperationalError("Test error", None, None)

        with patch.object(session_manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            with pytest.raises(TransactionException) as exc_info:
                await session_manager.execute_in_transaction(failing_operation)

            assert "Database transaction failed" in str(exc_info.value)

    async def test_health_check_success(self, session_manager):
        """Test successful health check."""
        mock_session = AsyncMock()

        with patch.object(session_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            with patch.object(
                session_manager, "get_transaction"
            ) as mock_get_transaction:
                mock_get_transaction.return_value.__aenter__.return_value = mock_session

                result = await session_manager.health_check(force=True)

                assert result["status"] == "healthy"
                assert "checks" in result
                assert "pool_info" in result
                assert result["checks"]["basic_query"]["status"] == "pass"
                assert result["checks"]["transaction"]["status"] == "pass"

    async def test_health_check_failure(self, session_manager):
        """Test health check with database failure."""
        with patch.object(session_manager, "get_session") as mock_get_session:
            mock_get_session.side_effect = OperationalError(
                "Connection failed", None, None
            )

            result = await session_manager.health_check(force=True)

            assert result["status"] == "unhealthy"
            assert "checks" in result
            assert result["checks"]["connection"]["status"] == "fail"

    async def test_initialize_database_success(self, session_manager, test_metadata):
        """Test successful database initialization."""
        from contextlib import asynccontextmanager

        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with patch.object(session_manager, "health_check") as mock_health:
            mock_health.return_value = {"status": "healthy"}

            # Create a proper async context manager mock for engine.begin()
            @asynccontextmanager
            async def mock_begin():
                yield mock_conn

            with patch.object(session_manager.engine, "begin", mock_begin):
                with patch.object(session_manager, "get_session") as mock_get_session:
                    mock_get_session.return_value.__aenter__.return_value = mock_session

                    result = await session_manager.initialize_database(test_metadata)

                    assert result is True
                    assert session_manager.is_initialized is True
                    mock_conn.run_sync.assert_called_once()

    async def test_initialize_database_failure(self, session_manager):
        """Test database initialization failure."""
        with patch.object(session_manager, "health_check") as mock_health:
            mock_health.return_value = {"status": "unhealthy"}

            result = await session_manager.initialize_database()

            assert result is False
            assert session_manager.is_initialized is False

    async def test_cleanup_database(self, session_manager, test_metadata):
        """Test database cleanup."""
        from contextlib import asynccontextmanager

        mock_conn = AsyncMock()

        # Create a proper async context manager mock for engine.begin()
        @asynccontextmanager
        async def mock_begin():
            yield mock_conn

        with patch.object(session_manager.engine, "begin", mock_begin):
            with patch.object(session_manager, "close_all_sessions") as mock_close:
                result = await session_manager.cleanup_database(
                    test_metadata, drop_all=True
                )

                assert result is True
                mock_conn.run_sync.assert_called_once()
                mock_close.assert_called_once()

    async def test_execute_with_retry_success(self, session_manager):
        """Test successful operation with retry logic."""
        mock_session = AsyncMock()
        expected_result = "success"

        async def test_operation(session):
            return expected_result

        with patch.object(session_manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            result = await session_manager.execute_with_retry(test_operation)

            assert result == expected_result

    async def test_execute_with_retry_transient_failure(self, session_manager):
        """Test retry logic with transient failures."""
        mock_session = AsyncMock()
        call_count = 0

        async def failing_operation(session):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DisconnectionError("Connection lost")
            return "success_after_retry"

        with patch.object(session_manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            result = await session_manager.execute_with_retry(
                failing_operation, max_retries=3, retry_delay=0.01
            )

            assert result == "success_after_retry"
            assert call_count == 3

    async def test_execute_with_retry_permanent_failure(self, session_manager):
        """Test retry logic with permanent failure."""
        mock_session = AsyncMock()

        async def failing_operation(session):
            raise DisconnectionError("Permanent connection failure")

        with patch.object(session_manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            with pytest.raises(DatabaseException) as exc_info:
                await session_manager.execute_with_retry(
                    failing_operation, max_retries=2, retry_delay=0.01
                )

            assert "failed after 3 attempts" in str(exc_info.value)

    async def test_get_pool_status(self, session_manager):
        """Test getting pool status information."""
        # Mock the engine URL to have a password that can be masked
        mock_url = MagicMock()
        mock_url.password = "secret_password"
        mock_url.__str__ = MagicMock(
            return_value="postgresql://user:secret_password@localhost:5432/testdb"
        )

        with patch.object(session_manager.engine, "url", mock_url):
            status = await session_manager.get_pool_status()

            assert "pool_class" in status
            assert "url" in status
            assert "size" in status
            assert "checked_in" in status
            assert "checked_out" in status
            assert status["pool_class"] == "QueuePool"
            assert "***" in status["url"]  # Password should be masked
            assert (
                "secret_password" not in status["url"]
            )  # Original password should not be visible


class TestGlobalSessionManager:
    """Test cases for global session manager functions."""

    async def test_initialize_and_get_session_manager(self, mock_engine):
        """Test global session manager initialization and retrieval."""
        manager = initialize_session_manager(mock_engine)

        assert isinstance(manager, SessionManager)
        assert get_session_manager() == manager

    async def test_get_session_manager_not_initialized(self):
        """Test getting session manager when not initialized."""
        # Reset global state
        import vet_core.database.session as session_module

        session_module._session_manager = None

        with pytest.raises(RuntimeError) as exc_info:
            get_session_manager()

        assert "not initialized" in str(exc_info.value)

    async def test_convenience_functions(self, mock_engine):
        """Test convenience functions work with global session manager."""
        manager = initialize_session_manager(mock_engine)
        mock_session = AsyncMock()

        # Test get_session convenience function
        with patch.object(manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            async with get_session() as session:
                assert session == mock_session

        # Test get_transaction convenience function
        with patch.object(manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            async with get_transaction() as session:
                assert session == mock_session

        # Test health_check convenience function
        with patch.object(manager, "health_check") as mock_health_check:
            mock_health_check.return_value = {"status": "healthy"}

            result = await health_check(force=True)
            assert result["status"] == "healthy"

        # Test execute_with_retry convenience function
        async def test_op(session):
            return "test_result"

        with patch.object(manager, "execute_with_retry") as mock_execute:
            mock_execute.return_value = "test_result"

            result = await execute_with_retry(test_op)
            assert result == "test_result"


@pytest.mark.integration
class TestSessionManagerIntegration:
    """Integration tests for session management (requires actual database)."""

    @pytest.fixture
    async def real_engine(self):
        """Create a real engine for integration testing."""
        # This would use a test database URL in real integration tests
        database_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"

        try:
            engine = create_engine(database_url, pool_size=2, max_overflow=0)
            yield engine
        finally:
            await engine.dispose()

    @pytest.mark.skip(reason="Requires actual PostgreSQL database")
    async def test_real_session_operations(self, real_engine):
        """Test session operations with real database."""
        manager = SessionManager(real_engine)

        # Test basic session operations
        async with manager.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Test transaction operations
        async with manager.get_transaction() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Test health check
        health = await manager.health_check(force=True)
        assert health["status"] == "healthy"

        # Test pool status
        pool_status = await manager.get_pool_status()
        assert "pool_class" in pool_status
