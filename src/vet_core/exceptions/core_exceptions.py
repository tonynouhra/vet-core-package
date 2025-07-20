"""
Core exceptions for the vet-core package.

This module defines the exception hierarchy and custom exceptions
used throughout the veterinary clinic platform.
"""

from typing import Any, Dict, Optional


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
        }
    
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
    ):
        """
        Initialize database exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            original_error: Original exception that caused this error
        """
        super().__init__(message, error_code, details)
        self.original_error = original_error
        
        if original_error and not details:
            self.details["original_error"] = str(original_error)


class ConnectionException(DatabaseException):
    """Exception raised when database connection fails."""
    
    def __init__(
        self,
        message: str = "Database connection failed",
        database_url: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize connection exception.
        
        Args:
            message: Error message
            database_url: Database URL (will be sanitized)
            original_error: Original exception
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
        )
    
    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove credentials from database URL for logging."""
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            # Remove username and password
            sanitized = parsed._replace(netloc=f"{parsed.hostname}:{parsed.port}")
            return urlunparse(sanitized)
        except Exception:
            return "[URL_PARSE_ERROR]"


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
            details["config_value"] = self._sanitize_config_value(config_key, config_value)
        
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