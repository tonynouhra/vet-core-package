"""
Custom exceptions for the vet core package.

This module defines the exception hierarchy and custom exceptions
used throughout the veterinary clinic platform.
"""

from .core_exceptions import (
    VetCoreException,
    DatabaseException,
    ConnectionException,
    TransactionException,
    MigrationException,
    ValidationException,
    SchemaValidationException,
    BusinessRuleException,
    ConfigurationException,
    DatabaseConfigException,
    EnvironmentException,
)

__all__ = [
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
]