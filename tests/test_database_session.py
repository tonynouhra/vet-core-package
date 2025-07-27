"""
Tests for database session management utilities.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from vet_core.database.session import (
    SessionManager,
    get_session,
    get_session_manager,
    get_transaction,
    initialize_session_manager,
)
from vet_core.exceptions import TransactionException


class TestSessionManager:
    """Test cases for SessionManager class."""

    def test_session_manager_initialization(self):
        """Test SessionManager initialization."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)

        assert manager.engine == mock_engine
        assert manager.session_factory is not None

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)

        with patch.object(manager, "session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value = mock_session

            session = await manager.create_session()

            assert session == mock_session
            mock_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_context_manager(self):
        """Test get_session context manager."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        with patch.object(manager, "create_session", return_value=mock_session):
            async with manager.get_session() as session:
                assert session == mock_session

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_with_exception(self):
        """Test get_session context manager with exception."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        with patch.object(manager, "create_session", return_value=mock_session):
            with pytest.raises(ValueError):
                async with manager.get_session() as session:
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transaction_context_manager(self):
        """Test get_transaction context manager."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock

        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        # Create a proper async context manager for session.begin()
        @asynccontextmanager
        async def mock_begin():
            yield None

        mock_session.begin = mock_begin

        with patch.object(manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            async with manager.get_transaction() as session:
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_execute_in_transaction_success(self):
        """Test execute_in_transaction with successful operation."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        async def test_operation(session, value):
            return value * 2

        with patch.object(manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            result = await manager.execute_in_transaction(test_operation, 5)

            assert result == 10

    @pytest.mark.asyncio
    async def test_execute_in_transaction_sqlalchemy_error(self):
        """Test execute_in_transaction with SQLAlchemy error."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        async def failing_operation(session):
            raise SQLAlchemyError("Database error")

        with patch.object(manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            with pytest.raises(TransactionException):
                await manager.execute_in_transaction(failing_operation)

    @pytest.mark.asyncio
    async def test_execute_in_transaction_general_error(self):
        """Test execute_in_transaction with general error."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        async def failing_operation(session):
            raise ValueError("General error")

        with patch.object(manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            with pytest.raises(TransactionException):
                await manager.execute_in_transaction(failing_operation)

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)
        mock_session = AsyncMock()

        with (
            patch.object(manager, "get_session") as mock_get_session,
            patch.object(manager, "get_transaction") as mock_get_transaction,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            result = await manager.health_check()

            assert isinstance(result, dict)
            assert result["status"] == "healthy"
            assert "checks" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        mock_engine = Mock()
        manager = SessionManager(mock_engine)

        with patch.object(manager, "get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Connection failed")

            result = await manager.health_check()

            assert isinstance(result, dict)
            assert result["status"] == "unhealthy"
            assert "checks" in result
            assert "general" in result["checks"]
            assert result["checks"]["general"]["status"] == "fail"


class TestGlobalSessionManager:
    """Test cases for global session manager functions."""

    def test_initialize_session_manager(self):
        """Test global session manager initialization."""
        mock_engine = Mock()

        manager = initialize_session_manager(mock_engine)

        assert isinstance(manager, SessionManager)
        assert manager.engine == mock_engine

    def test_get_session_manager_success(self):
        """Test getting initialized session manager."""
        mock_engine = Mock()

        # Initialize first
        initialize_session_manager(mock_engine)

        # Then get
        manager = get_session_manager()

        assert isinstance(manager, SessionManager)
        assert manager.engine == mock_engine

    def test_get_session_manager_not_initialized(self):
        """Test getting session manager when not initialized."""
        # Reset global state
        import vet_core.database.session

        vet_core.database.session._session_manager = None

        with pytest.raises(RuntimeError, match="Session manager not initialized"):
            get_session_manager()

    @pytest.mark.asyncio
    async def test_get_session_convenience_function(self):
        """Test get_session convenience function."""
        mock_engine = Mock()
        mock_session = AsyncMock()

        # Initialize session manager
        manager = initialize_session_manager(mock_engine)

        with patch.object(manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            async with get_session() as session:
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_transaction_convenience_function(self):
        """Test get_transaction convenience function."""
        mock_engine = Mock()
        mock_session = AsyncMock()

        # Initialize session manager
        manager = initialize_session_manager(mock_engine)

        with patch.object(manager, "get_transaction") as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session

            async with get_transaction() as session:
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_convenience_functions_not_initialized(self):
        """Test convenience functions when session manager not initialized."""
        # Reset global state
        import vet_core.database.session

        vet_core.database.session._session_manager = None

        with pytest.raises(RuntimeError):
            async with get_session():
                pass

        with pytest.raises(RuntimeError):
            async with get_transaction():
                pass
