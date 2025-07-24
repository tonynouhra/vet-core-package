"""
Custom exceptions for the vet core package.

This module defines the exception hierarchy and custom exceptions
used throughout the veterinary clinic platform.
"""

from .core_exceptions import (  # Utility functions
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

__all__ = [
    # Exception classes
    "VetCoreException",
    "DatabaseException",
    "ConnectionException",
    "TransactionException",
    "MigrationException",
    "ValidationException",
    "SchemaValidationException",
    "BusinessRuleException",
    "ConfigurationException",
    "DatabaseConfigException",
    "EnvironmentException",
    # Utility functions
    "format_validation_errors",
    "create_error_response",
    "handle_database_retry",
    "log_exception_context",
]
