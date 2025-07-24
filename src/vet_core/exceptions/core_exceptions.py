"""
Core exceptions for the vet-core package.

This module defines the exception hierarchy and custom exceptions
used throughout the veterinary clinic platform.
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urlunparse


class VetCoreException(Exception):
    """
    Base exception class for all vet-core package exceptions.

    Provides a consistent interface for error handling across the package.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": time.time(),
        }

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get detailed debug information for the exception.

        Returns:
            Dictionary with debug information including traceback
        """
        debug_info = self.to_dict()
        debug_info.update(
            {
                "traceback": (
                    traceback.format_exc()
                    if traceback.format_exc().strip() != "NoneType: None"
                    else None
                ),
                "module": self.__class__.__module__,
                "class_name": self.__class__.__name__,
            }
        )
        return debug_info

    def log_error(
        self, logger: Optional[logging.Logger] = None, level: int = logging.ERROR
    ) -> None:
        """
        Log the exception with appropriate level and context.

        Args:
            logger: Logger instance to use (creates default if None)
            level: Logging level to use
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        # Create structured log message
        log_data = {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

        logger.log(
            level,
            f"Exception occurred: {self.message}",
            extra={"exception_data": log_data},
        )

    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class DatabaseException(VetCoreException):
    """Base exception for database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        """
        Initialize database exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            original_error: Original exception that caused this error
            retry_count: Current retry attempt count
            max_retries: Maximum number of retry attempts
        """
        super().__init__(message, error_code, details)
        self.original_error = original_error
        self.retry_count = retry_count
        self.max_retries = max_retries

        if original_error and "original_error" not in self.details:
            self.details["original_error"] = str(original_error)

        self.details.update(
            {
                "retry_count": retry_count,
                "max_retries": max_retries,
                "retryable": self.is_retryable(),
            }
        )

    def is_retryable(self) -> bool:
        """
        Determine if this exception represents a retryable error.

        Returns:
            True if the operation can be retried, False otherwise
        """
        return self.retry_count < self.max_retries

    def get_retry_delay(self) -> float:
        """
        Calculate the delay before the next retry attempt using exponential backoff.

        Returns:
            Delay in seconds before next retry
        """
        if not self.is_retryable():
            return 0.0

        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        base_delay = 1.0
        return base_delay * (2**self.retry_count)

    def increment_retry(self) -> "DatabaseException":
        """
        Create a new exception instance with incremented retry count.

        Returns:
            New exception instance with incremented retry count
        """
        # For base DatabaseException
        if self.__class__ == DatabaseException:
            return DatabaseException(
                message=self.message,
                error_code=self.error_code,
                details=self.details.copy(),
                original_error=self.original_error,
                retry_count=self.retry_count + 1,
                max_retries=self.max_retries,
            )

        # For subclasses, we need to handle them specifically
        # This is a fallback that creates a new instance with updated retry count
        new_exception = self.__class__.__new__(self.__class__)
        new_exception.message = self.message
        new_exception.error_code = self.error_code
        new_exception.details = self.details.copy()
        new_exception.original_error = self.original_error
        new_exception.retry_count = self.retry_count + 1
        new_exception.max_retries = self.max_retries

        # Update details with new retry information
        new_exception.details.update(
            {
                "retry_count": new_exception.retry_count,
                "max_retries": new_exception.max_retries,
                "retryable": new_exception.is_retryable(),
            }
        )

        return new_exception


class ConnectionException(DatabaseException):
    """Exception raised when database connection fails."""

    def __init__(
        self,
        message: str = "Database connection failed",
        database_url: Optional[str] = None,
        original_error: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        """
        Initialize connection exception.

        Args:
            message: Error message
            database_url: Database URL (will be sanitized)
            original_error: Original exception
            retry_count: Current retry attempt count
            max_retries: Maximum number of retry attempts
        """
        details = {}
        if database_url:
            # Sanitize URL to remove credentials
            sanitized_url = self._sanitize_url(database_url)
            details["database_url"] = sanitized_url

        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            details=details,
            original_error=original_error,
            retry_count=retry_count,
            max_retries=max_retries,
        )

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove credentials from database URL for logging."""
        try:
            parsed = urlparse(url)
            # Remove username and password
            sanitized = parsed._replace(netloc=f"{parsed.hostname}:{parsed.port}")
            return urlunparse(sanitized)
        except (ValueError, AttributeError) as e:
            return f"[URL_PARSE_ERROR: {e}]"

    def is_retryable(self) -> bool:
        """
        Determine if this connection error is retryable.

        Connection errors are generally retryable unless they indicate
        authentication or configuration issues.
        """
        if not super().is_retryable():
            return False

        # Check if the error indicates a non-retryable condition
        if self.original_error:
            error_str = str(self.original_error).lower()
            non_retryable_patterns = [
                "authentication failed",
                "invalid credentials",
                "access denied",
                "permission denied",
                "database does not exist",
                "role does not exist",
            ]
            if any(pattern in error_str for pattern in non_retryable_patterns):
                return False

        return True

    def increment_retry(self) -> "ConnectionException":
        """
        Create a new ConnectionException instance with incremented retry count.

        Returns:
            New ConnectionException instance with incremented retry count
        """
        database_url = None
        if "database_url" in self.details:
            # We need to reconstruct the original URL for the new instance
            database_url = self.details["database_url"]

        return ConnectionException(
            message=self.message,
            database_url=database_url,
            original_error=self.original_error,
            retry_count=self.retry_count + 1,
            max_retries=self.max_retries,
        )


class TransactionException(DatabaseException):
    """Exception raised when database transaction fails."""

    def __init__(
        self,
        message: str = "Database transaction failed",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize transaction exception.

        Args:
            message: Error message
            operation: Description of the failed operation
            original_error: Original exception
        """
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code="DATABASE_TRANSACTION_ERROR",
            details=details,
            original_error=original_error,
        )

    def increment_retry(self) -> "TransactionException":
        """
        Create a new TransactionException instance with incremented retry count.

        Returns:
            New TransactionException instance with incremented retry count
        """
        operation = self.details.get("operation")
        return TransactionException(
            message=self.message,
            operation=operation,
            original_error=self.original_error,
        )


class MigrationException(DatabaseException):
    """Exception raised when database migration fails."""

    def __init__(
        self,
        message: str = "Database migration failed",
        migration_version: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize migration exception.

        Args:
            message: Error message
            migration_version: Version of the failed migration
            original_error: Original exception
        """
        details = {}
        if migration_version:
            details["migration_version"] = migration_version

        super().__init__(
            message=message,
            error_code="DATABASE_MIGRATION_ERROR",
            details=details,
            original_error=original_error,
        )

    def increment_retry(self) -> "MigrationException":
        """
        Create a new MigrationException instance with incremented retry count.

        Returns:
            New MigrationException instance with incremented retry count
        """
        migration_version = self.details.get("migration_version")
        return MigrationException(
            message=self.message,
            migration_version=migration_version,
            original_error=self.original_error,
        )


class ValidationException(VetCoreException):
    """Base exception for data validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_errors: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Field that failed validation
            value: Value that failed validation
            validation_errors: Detailed validation errors
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class SchemaValidationException(ValidationException):
    """Exception raised when Pydantic schema validation fails."""

    def __init__(
        self,
        message: str = "Schema validation failed",
        schema_name: Optional[str] = None,
        validation_errors: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize schema validation exception.

        Args:
            message: Error message
            schema_name: Name of the schema that failed validation
            validation_errors: Pydantic validation errors
        """
        details = {}
        if schema_name:
            details["schema_name"] = schema_name

        super().__init__(
            message=message,
            field=None,
            value=None,
            validation_errors=validation_errors,
        )
        self.error_code = "SCHEMA_VALIDATION_ERROR"
        if details:
            self.details.update(details)


class BusinessRuleException(ValidationException):
    """Exception raised when business rule validation fails."""

    def __init__(
        self,
        message: str = "Business rule validation failed",
        rule_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize business rule exception.

        Args:
            message: Error message
            rule_name: Name of the business rule that failed
            context: Additional context about the failure
        """
        details = {}
        if rule_name:
            details["rule_name"] = rule_name
        if context:
            details["context"] = context

        super().__init__(
            message=message,
            field=None,
            value=None,
            validation_errors=None,
        )
        self.error_code = "BUSINESS_RULE_ERROR"
        if details:
            self.details.update(details)


class ConfigurationException(VetCoreException):
    """Base exception for configuration-related errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
    ):
        """
        Initialize configuration exception.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Configuration value (will be sanitized)
        """
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value:
            # Sanitize sensitive configuration values
            details["config_value"] = self._sanitize_config_value(
                config_key, config_value
            )

        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details,
        )

    @staticmethod
    def _sanitize_config_value(key: Optional[str], value: str) -> str:
        """Sanitize configuration values to avoid exposing secrets."""
        if not key:
            return "[REDACTED]"

        sensitive_keys = ["password", "secret", "key", "token", "credential"]
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            return "[REDACTED]"

        return value


class DatabaseConfigException(ConfigurationException):
    """Exception raised when database configuration is invalid."""

    def __init__(
        self,
        message: str = "Database configuration error",
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
    ):
        """
        Initialize database configuration exception.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Configuration value
        """
        super().__init__(message, config_key, config_value)
        self.error_code = "DATABASE_CONFIG_ERROR"


class EnvironmentException(ConfigurationException):
    """Exception raised when environment configuration is invalid."""

    def __init__(
        self,
        message: str = "Environment configuration error",
        env_var: Optional[str] = None,
        env_value: Optional[str] = None,
    ):
        """
        Initialize environment exception.

        Args:
            message: Error message
            env_var: Environment variable that caused the error
            env_value: Environment variable value
        """
        super().__init__(message, env_var, env_value)
        self.error_code = "ENVIRONMENT_ERROR"


# Utility functions for exception handling and error formatting


def format_validation_errors(errors: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Format Pydantic validation errors into a user-friendly structure.

    Args:
        errors: List of Pydantic validation errors

    Returns:
        Dictionary mapping field names to lists of error messages
    """
    formatted_errors = {}

    for error in errors:
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        if not field_path:
            field_path = "root"

        message = error.get("msg", "Validation error")
        error_type = error.get("type", "unknown")

        # Create a more user-friendly error message
        if error_type == "value_error":
            formatted_message = message
        elif error_type == "type_error":
            formatted_message = f"Invalid type: {message}"
        elif error_type == "missing":
            formatted_message = "This field is required"
        else:
            formatted_message = f"{message} (type: {error_type})"

        if field_path not in formatted_errors:
            formatted_errors[field_path] = []
        formatted_errors[field_path].append(formatted_message)

    return formatted_errors


def create_error_response(
    exception: VetCoreException,
    include_debug: bool = False,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Create a standardized error response from an exception.

    Args:
        exception: The exception to format
        include_debug: Whether to include debug information
        include_traceback: Whether to include traceback information

    Returns:
        Standardized error response dictionary
    """
    response = {
        "success": False,
        "error": {
            "type": exception.__class__.__name__,
            "code": exception.error_code,
            "message": exception.message,
        },
    }

    # Add details if they exist
    if exception.details:
        response["error"]["details"] = exception.details

    # Add debug information if requested
    if include_debug:
        debug_info = exception.get_debug_info()
        response["debug"] = {
            "timestamp": debug_info["timestamp"],
            "module": debug_info["module"],
            "class_name": debug_info["class_name"],
        }

        if include_traceback and debug_info.get("traceback"):
            response["debug"]["traceback"] = debug_info["traceback"]

    return response


def handle_database_retry(
    operation_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    logger: Optional[logging.Logger] = None,
):
    """
    Decorator for handling database operations with retry logic.

    Args:
        operation_name: Name of the operation for logging
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        logger: Logger instance to use

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            if logger is None:
                operation_logger = logging.getLogger(__name__)
            else:
                operation_logger = logger

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except DatabaseException as e:
                    last_exception = e

                    if not e.is_retryable() or attempt == max_retries:
                        operation_logger.error(
                            f"Database operation '{operation_name}' failed after {attempt + 1} attempts",
                            extra={"exception_data": e.to_dict()},
                        )
                        raise

                    # Calculate delay and wait
                    delay = base_delay * (2**attempt)
                    operation_logger.warning(
                        f"Database operation '{operation_name}' failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s",
                        extra={"exception_data": e.to_dict()},
                    )

                    await asyncio.sleep(delay)

                    # Create new exception with incremented retry count
                    last_exception = e.increment_retry()
                except Exception as e:
                    # Non-database exceptions are not retryable
                    operation_logger.error(
                        f"Non-retryable error in database operation '{operation_name}'",
                        extra={"error": str(e)},
                    )
                    raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def log_exception_context(
    exception: Exception,
    context: Dict[str, Any],
    logger: Optional[logging.Logger] = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log an exception with additional context information.

    Args:
        exception: The exception to log
        context: Additional context information
        logger: Logger instance to use
        level: Logging level
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if isinstance(exception, VetCoreException):
        log_data = exception.to_dict()
        log_data["context"] = context
        logger.log(
            level,
            f"Exception with context: {exception.message}",
            extra={"exception_data": log_data},
        )
    else:
        logger.log(
            level,
            f"Non-VetCore exception: {str(exception)}",
            extra={
                "exception_type": exception.__class__.__name__,
                "exception_message": str(exception),
                "context": context,
            },
        )
