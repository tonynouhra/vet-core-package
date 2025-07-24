"""
Tests for database connection utilities.
"""

from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlparse

import pytest

from vet_core.database.connection import (
    DatabaseConfig,
    close_engine,
    create_engine,
    get_database_url,
    test_connection,
    wait_for_database,
)
from vet_core.exceptions import ConnectionException


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""

    def test_valid_database_url(self):
        """Test DatabaseConfig with valid URL."""
        url = "postgresql://user:pass@localhost:5432/testdb"
        config = DatabaseConfig(url)

        assert config.database_url == url
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
        assert config.echo is False
        assert config.echo_pool is False

    def test_custom_parameters(self):
        """Test DatabaseConfig with custom parameters."""
        url = "postgresql://user:pass@localhost:5432/testdb"
        config = DatabaseConfig(
            database_url=url, pool_size=5, max_overflow=10, echo=True
        )

        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.echo is True

    def test_invalid_database_url_scheme(self):
        """Test DatabaseConfig with invalid URL scheme."""
        with pytest.raises(ValueError, match="Database URL must use postgresql"):
            DatabaseConfig("mysql://user:pass@localhost:5432/testdb")

    def test_invalid_database_url_no_hostname(self):
        """Test DatabaseConfig with URL missing hostname."""
        with pytest.raises(ValueError, match="Database URL must include hostname"):
            DatabaseConfig("postgresql://user:pass@:5432/testdb")

    def test_invalid_database_url_no_database(self):
        """Test DatabaseConfig with URL missing database name."""
        with pytest.raises(ValueError, match="Database URL must include database name"):
            DatabaseConfig("postgresql://user:pass@localhost:5432/")

    def test_get_async_url_conversion(self):
        """Test conversion to async URL format."""
        config = DatabaseConfig("postgresql://user:pass@localhost:5432/testdb")
        async_url = config.get_async_url()

        assert async_url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"

    def test_get_async_url_already_async(self):
        """Test async URL remains unchanged."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        config = DatabaseConfig(url)
        async_url = config.get_async_url()

        assert async_url == url


class TestCreateEngine:
    """Test cases for create_engine function."""

    @patch("vet_core.database.connection.create_async_engine")
    def test_create_engine_success(self, mock_create_async_engine):
        """Test successful engine creation."""
        mock_engine = Mock()
        mock_create_async_engine.return_value = mock_engine

        url = "postgresql://user:pass@localhost:5432/testdb"
        engine = create_engine(url)

        assert engine == mock_engine
        mock_create_async_engine.assert_called_once()

        # Check that the URL was converted to async format
        call_args = mock_create_async_engine.call_args
        assert call_args[0][0] == "postgresql+asyncpg://user:pass@localhost:5432/testdb"

    @patch("vet_core.database.connection.create_async_engine")
    def test_create_engine_with_null_pool(self, mock_create_async_engine):
        """Test engine creation with null pool."""
        mock_engine = Mock()
        mock_create_async_engine.return_value = mock_engine

        url = "postgresql://user:pass@localhost:5432/testdb"
        engine = create_engine(url, use_null_pool=True)

        assert engine == mock_engine

        # Check that NullPool was used
        call_args = mock_create_async_engine.call_args
        assert "poolclass" in call_args[1]

    def test_create_engine_invalid_url(self):
        """Test engine creation with invalid URL."""
        with pytest.raises(ValueError):
            create_engine("invalid://url")


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_get_database_url_with_password(self):
        """Test database URL construction with password."""
        url = get_database_url(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )

        expected = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert url == expected

    def test_get_database_url_without_password(self):
        """Test database URL construction without password."""
        url = get_database_url(host="localhost", database="testdb", username="user")

        expected = "postgresql+asyncpg://user@localhost:5432/testdb"
        assert url == expected

    def test_get_database_url_custom_driver(self):
        """Test database URL construction with custom driver."""
        url = get_database_url(
            host="localhost", database="testdb", username="user", driver="psycopg2"
        )

        expected = "postgresql+psycopg2://user@localhost:5432/testdb"
        assert url == expected


class TestConnectionTesting:
    """Test cases for connection testing functions."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn

        result = await test_connection(mock_engine, max_retries=0)

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test failure."""
        mock_engine = Mock()
        mock_engine.begin.side_effect = Exception("Connection failed")

        result = await test_connection(mock_engine, max_retries=0)

        assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_with_retries(self):
        """Test connection test with retries."""
        mock_engine = Mock()
        # First call fails, second succeeds
        mock_engine.begin.side_effect = [
            Exception("Connection failed"),
            AsyncMock().__aenter__.return_value,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await test_connection(mock_engine, max_retries=1, retry_delay=0.1)

        assert result is True
        assert mock_engine.begin.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_database_success(self):
        """Test wait_for_database with successful connection."""
        mock_engine = Mock()

        with patch("vet_core.database.connection.test_connection", return_value=True):
            result = await wait_for_database(
                mock_engine, timeout=1.0, check_interval=0.1
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_database_timeout(self):
        """Test wait_for_database with timeout."""
        mock_engine = Mock()

        with patch("vet_core.database.connection.test_connection", return_value=False):
            with pytest.raises(ConnectionException):
                await wait_for_database(mock_engine, timeout=0.1, check_interval=0.05)

    @pytest.mark.asyncio
    async def test_close_engine_success(self):
        """Test successful engine closure."""
        mock_engine = AsyncMock()

        await close_engine(mock_engine)

        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_engine_error(self):
        """Test engine closure with error."""
        mock_engine = AsyncMock()
        mock_engine.dispose.side_effect = Exception("Close failed")

        # Should not raise exception
        await close_engine(mock_engine)
