"""
Tests for exception handling in the vet-core package.
"""

import asyncio
import logging
from unittest.mock import Mock, patch

import pytest

from vet_core.exceptions import (  # Utility functions
    BusinessRuleException,
    ConfigurationException,
    ConnectionException,
    DatabaseConfigException,
    DatabaseException,
    EnvironmentException,
    MigrationException,
    SchemaValidationException,
    TransactionException,
    ValidationException,
    VetCoreException,
    create_error_response,
    format_validation_errors,
    handle_database_retry,
    log_exception_context,
)


class TestVetCoreException:
    """Test cases for the base VetCoreException class."""

    def test_basic_exception_creation(self):
        """Test creating a basic exception."""
        exc = VetCoreException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "VetCoreException"
        assert exc.details == {}

    def test_exception_with_error_code(self):
        """Test creating exception with custom error code."""
        exc = VetCoreException("Test error", error_code="CUSTOM_ERROR")

        assert exc.error_code == "CUSTOM_ERROR"

    def test_exception_with_details(self):
        """Test creating exception with details."""
        details = {"field": "test_field", "value": "test_value"}
        exc = VetCoreException("Test error", details=details)

        assert exc.details == details
        assert "Details: " in str(exc)

    def test_to_dict_method(self):
        """Test converting exception to dictionary."""
        details = {"field": "test_field"}
        exc = VetCoreException("Test error", error_code="TEST_ERROR", details=details)

        result = exc.to_dict()

        assert result["error_type"] == "VetCoreException"
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == details


class TestDatabaseException:
    """Test cases for DatabaseException and its subclasses."""

    def test_database_exception_creation(self):
        """Test creating a database exception."""
        original_error = Exception("Original error")
        exc = DatabaseException("Database error", original_error=original_error)

        assert exc.message == "Database error"
        assert exc.original_error == original_error
        assert "Original error" in exc.details["original_error"]

    def test_connection_exception_creation(self):
        """Test creating a connection exception."""
        exc = ConnectionException(
            "Connection failed", database_url="postgresql://user:pass@localhost/db"
        )

        assert exc.message == "Connection failed"
        assert exc.error_code == "DATABASE_CONNECTION_ERROR"
        assert "localhost" in exc.details["database_url"]
        # Ensure credentials are sanitized
        assert "pass" not in exc.details["database_url"]

    def test_connection_exception_url_sanitization(self):
        """Test URL sanitization in connection exception."""
        url = "postgresql://user:secret@localhost:5432/testdb"
        exc = ConnectionException(database_url=url)

        sanitized_url = exc.details["database_url"]
        assert "secret" not in sanitized_url
        assert "localhost:5432" in sanitized_url

    def test_transaction_exception_creation(self):
        """Test creating a transaction exception."""
        exc = TransactionException("Transaction failed", operation="INSERT INTO users")

        assert exc.message == "Transaction failed"
        assert exc.error_code == "DATABASE_TRANSACTION_ERROR"
        assert exc.details["operation"] == "INSERT INTO users"

    def test_migration_exception_creation(self):
        """Test creating a migration exception."""
        exc = MigrationException("Migration failed", migration_version="001_initial")

        assert exc.message == "Migration failed"
        assert exc.error_code == "DATABASE_MIGRATION_ERROR"
        assert exc.details["migration_version"] == "001_initial"


class TestValidationException:
    """Test cases for ValidationException and its subclasses."""

    def test_validation_exception_creation(self):
        """Test creating a validation exception."""
        exc = ValidationException(
            "Validation failed", field="email", value="invalid-email"
        )

        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"
        assert exc.details["value"] == "invalid-email"

    def test_validation_exception_with_errors(self):
        """Test validation exception with detailed errors."""
        validation_errors = {
            "email": ["Invalid email format"],
            "age": ["Must be positive integer"],
        }
        exc = ValidationException(
            "Multiple validation errors", validation_errors=validation_errors
        )

        assert exc.details["validation_errors"] == validation_errors

    def test_schema_validation_exception_creation(self):
        """Test creating a schema validation exception."""
        validation_errors = {"field": ["error message"]}
        exc = SchemaValidationException(
            "Schema validation failed",
            schema_name="UserCreateSchema",
            validation_errors=validation_errors,
        )

        assert exc.error_code == "SCHEMA_VALIDATION_ERROR"
        assert exc.details["schema_name"] == "UserCreateSchema"
        assert exc.details["validation_errors"] == validation_errors

    def test_business_rule_exception_creation(self):
        """Test creating a business rule exception."""
        context = {"user_id": "123", "appointment_time": "2024-01-01T10:00:00"}
        exc = BusinessRuleException(
            "Appointment outside business hours",
            rule_name="business_hours_check",
            context=context,
        )

        assert exc.error_code == "BUSINESS_RULE_ERROR"
        assert exc.details["rule_name"] == "business_hours_check"
        assert exc.details["context"] == context


class TestConfigurationException:
    """Test cases for ConfigurationException and its subclasses."""

    def test_configuration_exception_creation(self):
        """Test creating a configuration exception."""
        exc = ConfigurationException(
            "Invalid configuration",
            config_key="database_url",
            config_value="invalid-url",
        )

        assert exc.message == "Invalid configuration"
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details["config_key"] == "database_url"
        assert exc.details["config_value"] == "invalid-url"

    def test_configuration_exception_sensitive_value_sanitization(self):
        """Test sanitization of sensitive configuration values."""
        exc = ConfigurationException(
            "Invalid config", config_key="database_password", config_value="secret123"
        )

        assert exc.details["config_value"] == "[REDACTED]"

    def test_database_config_exception_creation(self):
        """Test creating a database configuration exception."""
        exc = DatabaseConfigException(
            "Invalid database config", config_key="pool_size", config_value="invalid"
        )

        assert exc.error_code == "DATABASE_CONFIG_ERROR"
        assert exc.details["config_key"] == "pool_size"

    def test_environment_exception_creation(self):
        """Test creating an environment exception."""
        exc = EnvironmentException(
            "Missing environment variable", env_var="DATABASE_URL", env_value=None
        )

        assert exc.error_code == "ENVIRONMENT_ERROR"
        assert exc.details["config_key"] == "DATABASE_URL"


class TestExceptionHierarchy:
    """Test cases for exception hierarchy and inheritance."""

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from VetCoreException."""
        exceptions = [
            DatabaseException("test"),
            ConnectionException("test"),
            TransactionException("test"),
            MigrationException("test"),
            ValidationException("test"),
            SchemaValidationException("test"),
            BusinessRuleException("test"),
            ConfigurationException("test"),
            DatabaseConfigException("test"),
            EnvironmentException("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, VetCoreException)

    def test_database_exception_inheritance(self):
        """Test that database exceptions inherit from DatabaseException."""
        database_exceptions = [
            ConnectionException("test"),
            TransactionException("test"),
            MigrationException("test"),
        ]

        for exc in database_exceptions:
            assert isinstance(exc, DatabaseException)

    def test_validation_exception_inheritance(self):
        """Test that validation exceptions inherit from ValidationException."""
        validation_exceptions = [
            SchemaValidationException("test"),
            BusinessRuleException("test"),
        ]

        for exc in validation_exceptions:
            assert isinstance(exc, ValidationException)

    def test_configuration_exception_inheritance(self):
        """Test that configuration exceptions inherit from ConfigurationException."""
        config_exceptions = [
            DatabaseConfigException("test"),
            EnvironmentException("test"),
        ]

        for exc in config_exceptions:
            assert isinstance(exc, ConfigurationException)


class TestExceptionUtilities:
    """Test cases for exception utility methods."""

    def test_url_sanitization_edge_cases(self):
        """Test URL sanitization with various edge cases."""
        # Test with no credentials
        exc = ConnectionException(database_url="postgresql://localhost/db")
        assert "localhost" in exc.details["database_url"]

        # Test with malformed URL
        exc = ConnectionException(database_url="not-a-url")
        assert exc.details["database_url"] == "[URL_PARSE_ERROR]"

    def test_config_value_sanitization_edge_cases(self):
        """Test configuration value sanitization with edge cases."""
        # Test with None key
        exc = ConfigurationException(config_key=None, config_value="test")
        assert exc.details["config_value"] == "[REDACTED]"

        # Test with various sensitive key patterns
        sensitive_keys = ["password", "secret", "key", "token", "credential"]
        for key in sensitive_keys:
            exc = ConfigurationException(
                config_key=f"test_{key}", config_value="sensitive"
            )
            assert exc.details["config_value"] == "[REDACTED]"

    def test_exception_chaining(self):
        """Test exception chaining with original errors."""
        original = ValueError("Original error")
        db_exc = DatabaseException("Database error", original_error=original)

        assert db_exc.original_error == original
        assert "Original error" in db_exc.details["original_error"]

    def test_exception_serialization(self):
        """Test that exceptions can be properly serialized."""
        exc = ValidationException(
            "Validation failed",
            field="email",
            value="test@example.com",
            validation_errors={"email": ["Invalid format"]},
        )

        serialized = exc.to_dict()

        # Ensure all fields are serializable
        import json

        json_str = json.dumps(serialized)
        assert json_str is not None

        # Verify structure
        assert "error_type" in serialized
        assert "error_code" in serialized
        assert "message" in serialized
        assert "details" in serialized


class TestExceptionIntegration:
    """Test cases for exception integration with other components."""

    def test_exception_with_retry_logic(self):
        """Test exceptions work properly with retry mechanisms."""
        # Simulate a connection exception that might trigger retry
        exc = ConnectionException(
            "Connection timeout", database_url="postgresql://localhost/test"
        )

        # Verify exception contains information useful for retry logic
        assert exc.error_code == "DATABASE_CONNECTION_ERROR"
        assert "database_url" in exc.details

        # Test that exception can be re-raised after retry attempts
        try:
            raise exc
        except ConnectionException as caught:
            assert caught.message == "Connection timeout"
            assert caught.error_code == "DATABASE_CONNECTION_ERROR"

    def test_exception_logging_compatibility(self):
        """Test that exceptions work well with logging systems."""
        exc = DatabaseException(
            "Database operation failed",
            error_code="DB_ERROR",
            details={"table": "users", "operation": "INSERT"},
        )

        # Test string representation for logging
        log_message = str(exc)
        assert "Database operation failed" in log_message
        assert "table" in log_message
        assert "operation" in log_message

        # Test dictionary representation for structured logging
        log_dict = exc.to_dict()
        assert log_dict["error_type"] == "DatabaseException"
        assert log_dict["details"]["table"] == "users"


class TestExceptionEnhancements:
    """Test cases for enhanced exception functionality."""

    def test_exception_debug_info(self):
        """Test getting debug information from exceptions."""
        exc = VetCoreException("Test error", error_code="TEST_ERROR")
        debug_info = exc.get_debug_info()

        assert "timestamp" in debug_info
        assert debug_info["error_type"] == "VetCoreException"
        assert debug_info["error_code"] == "TEST_ERROR"
        assert debug_info["module"] == "vet_core.exceptions.core_exceptions"
        assert debug_info["class_name"] == "VetCoreException"

    @patch("vet_core.exceptions.core_exceptions.logging.getLogger")
    def test_exception_logging(self, mock_get_logger):
        """Test exception logging functionality."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = VetCoreException("Test error", error_code="TEST_ERROR")
        exc.log_error()

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR
        assert "Exception occurred: Test error" in call_args[0][1]

    def test_database_exception_retry_logic(self):
        """Test database exception retry logic enhancements."""
        exc = DatabaseException("DB error", retry_count=0, max_retries=3)

        assert exc.is_retryable() is True
        assert exc.get_retry_delay() == 1.0

        # Test retry increment
        new_exc = exc.increment_retry()
        assert new_exc.retry_count == 1
        assert new_exc.get_retry_delay() == 2.0

        # Test max retries reached
        max_exc = DatabaseException("DB error", retry_count=3, max_retries=3)
        assert max_exc.is_retryable() is False
        assert max_exc.get_retry_delay() == 0.0


class TestUtilityFunctions:
    """Test cases for exception utility functions."""

    def test_format_validation_errors(self):
        """Test formatting Pydantic validation errors."""
        pydantic_errors = [
            {"loc": ["email"], "msg": "field required", "type": "missing"},
            {
                "loc": ["age"],
                "msg": "ensure this value is greater than 0",
                "type": "value_error",
            },
            {
                "loc": ["name", "first"],
                "msg": "str type expected",
                "type": "type_error",
            },
        ]

        formatted = format_validation_errors(pydantic_errors)

        assert "email" in formatted
        assert formatted["email"] == ["This field is required"]
        assert "age" in formatted
        assert "ensure this value is greater than 0" in formatted["age"][0]
        assert "name.first" in formatted
        assert "Invalid type:" in formatted["name.first"][0]

    def test_create_error_response_basic(self):
        """Test creating basic error response."""
        exc = VetCoreException("Test error", error_code="TEST_ERROR")
        response = create_error_response(exc)

        assert response["success"] is False
        assert response["error"]["type"] == "VetCoreException"
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error"

    def test_create_error_response_with_debug(self):
        """Test creating error response with debug information."""
        exc = VetCoreException("Test error", error_code="TEST_ERROR")
        response = create_error_response(exc, include_debug=True)

        assert "debug" in response
        assert "timestamp" in response["debug"]
        assert response["debug"]["module"] == "vet_core.exceptions.core_exceptions"
        assert response["debug"]["class_name"] == "VetCoreException"

    def test_create_error_response_with_details(self):
        """Test creating error response with exception details."""
        details = {"field": "email", "value": "invalid"}
        exc = ValidationException("Validation failed", details=details)
        response = create_error_response(exc)

        assert "details" in response["error"]
        assert response["error"]["details"] == details

    @patch("vet_core.exceptions.core_exceptions.logging.getLogger")
    def test_log_exception_context(self, mock_get_logger):
        """Test logging exceptions with context."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = VetCoreException("Test error")
        context = {"user_id": "123", "operation": "create_user"}

        log_exception_context(exc, context)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR
        assert "Exception with context: Test error" in call_args[0][1]
        assert "exception_data" in call_args[1]["extra"]

    @patch("vet_core.exceptions.core_exceptions.logging.getLogger")
    def test_log_non_vetcore_exception_context(self, mock_get_logger):
        """Test logging non-VetCore exceptions with context."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = ValueError("Standard Python error")
        context = {"operation": "test"}

        log_exception_context(exc, context)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert "Non-VetCore exception: Standard Python error" in call_args[0][1]
        assert call_args[1]["extra"]["exception_type"] == "ValueError"


class TestDatabaseRetryDecorator:
    """Test cases for database retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test decorator with successful operation."""

        @handle_database_retry("test_operation", max_retries=2)
        async def successful_operation():
            return "success"

        result = await successful_operation()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retryable_database_exception(self):
        """Test decorator with retryable database exception."""
        call_count = 0

        @handle_database_retry("test_operation", max_retries=2, base_delay=0.01)
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseException(
                    "Connection failed", retry_count=call_count - 1, max_retries=2
                )
            return "success"

        result = await failing_operation()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_database_exception(self):
        """Test decorator with non-retryable database exception."""

        @handle_database_retry("test_operation", max_retries=2)
        async def failing_operation():
            raise DatabaseException(
                "Auth failed", retry_count=3, max_retries=2
            )  # Not retryable

        with pytest.raises(DatabaseException) as exc_info:
            await failing_operation()

        assert "Auth failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_database_exception(self):
        """Test decorator with non-database exception."""

        @handle_database_retry("test_operation", max_retries=2)
        async def failing_operation():
            raise ValueError("Not a database error")

        with pytest.raises(ValueError) as exc_info:
            await failing_operation()

        assert "Not a database error" in str(exc_info.value)


class TestConnectionExceptionRetryLogic:
    """Test cases for connection exception retry logic."""

    def test_connection_exception_retryable_conditions(self):
        """Test connection exception retry logic for various conditions."""
        # Test retryable connection error
        exc = ConnectionException("Connection timeout")
        assert exc.is_retryable() is True

        # Test non-retryable authentication error
        auth_error = Exception("authentication failed")
        exc = ConnectionException("Auth failed", original_error=auth_error)
        assert exc.is_retryable() is False

        # Test non-retryable permission error
        perm_error = Exception("permission denied")
        exc = ConnectionException("Permission denied", original_error=perm_error)
        assert exc.is_retryable() is False

        # Test non-retryable database not found error
        db_error = Exception("database does not exist")
        exc = ConnectionException("DB not found", original_error=db_error)
        assert exc.is_retryable() is False

    def test_connection_exception_max_retries_reached(self):
        """Test connection exception when max retries is reached."""
        exc = ConnectionException("Connection failed", retry_count=3, max_retries=3)
        assert exc.is_retryable() is False
