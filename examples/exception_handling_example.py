#!/usr/bin/env python3
"""
Example demonstrating comprehensive exception handling in vet-core package.

This example shows how to use the various exception types and utility functions
for robust error handling in veterinary clinic applications.
"""

import asyncio
import logging
from typing import Dict, Any

from vet_core.exceptions import (
    VetCoreException,
    DatabaseException,
    ConnectionException,
    ValidationException,
    SchemaValidationException,
    BusinessRuleException,
    ConfigurationException,
    format_validation_errors,
    create_error_response,
    handle_database_retry,
    log_exception_context,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demonstrate_basic_exceptions():
    """Demonstrate basic exception usage."""
    print("\n=== Basic Exception Usage ===")
    
    try:
        # Simulate a validation error
        raise ValidationException(
            "Pet age validation failed",
            field="age",
            value=-5,
            validation_errors={"age": ["Age must be positive"]}
        )
    except ValidationException as e:
        print(f"Caught validation exception: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Details: {e.details}")
        
        # Log the exception
        e.log_error(logger)
        
        # Get debug information
        debug_info = e.get_debug_info()
        print(f"Debug info available: {list(debug_info.keys())}")


def demonstrate_database_exceptions():
    """Demonstrate database exception handling with retry logic."""
    print("\n=== Database Exception Handling ===")
    
    try:
        # Simulate a database connection error
        original_error = Exception("Connection refused")
        raise ConnectionException(
            "Failed to connect to database",
            database_url="postgresql://user:password@localhost:5432/vetclinic",
            original_error=original_error
        )
    except ConnectionException as e:
        print(f"Caught connection exception: {e}")
        print(f"Is retryable: {e.is_retryable()}")
        print(f"Retry delay: {e.get_retry_delay()}s")
        print(f"URL sanitized: {'password' not in str(e.details)}")
        
        # Demonstrate retry increment
        retry_exc = e.increment_retry()
        print(f"After retry increment - count: {retry_exc.retry_count}, delay: {retry_exc.get_retry_delay()}s")


def demonstrate_validation_error_formatting():
    """Demonstrate validation error formatting utilities."""
    print("\n=== Validation Error Formatting ===")
    
    # Simulate Pydantic validation errors
    pydantic_errors = [
        {"loc": ["email"], "msg": "field required", "type": "missing"},
        {"loc": ["age"], "msg": "ensure this value is greater than 0", "type": "value_error"},
        {"loc": ["pet", "name"], "msg": "str type expected", "type": "type_error"},
        {"loc": ["appointment_time"], "msg": "invalid datetime format", "type": "value_error"},
    ]
    
    formatted_errors = format_validation_errors(pydantic_errors)
    print("Formatted validation errors:")
    for field, messages in formatted_errors.items():
        print(f"  {field}: {messages}")
    
    # Create a schema validation exception
    schema_exc = SchemaValidationException(
        "Pet creation schema validation failed",
        schema_name="PetCreateSchema",
        validation_errors=formatted_errors
    )
    
    # Create standardized error response
    error_response = create_error_response(schema_exc, include_debug=True)
    print(f"\nStandardized error response: {error_response}")


def demonstrate_business_rule_exceptions():
    """Demonstrate business rule exception handling."""
    print("\n=== Business Rule Exceptions ===")
    
    try:
        # Simulate a business rule violation
        context = {
            "appointment_time": "2024-01-01T22:00:00",
            "clinic_hours": "09:00-18:00",
            "user_id": "user_123"
        }
        
        raise BusinessRuleException(
            "Appointment scheduled outside business hours",
            rule_name="business_hours_validation",
            context=context
        )
    except BusinessRuleException as e:
        print(f"Business rule violation: {e}")
        
        # Log with additional context
        additional_context = {"service_type": "emergency", "priority": "high"}
        log_exception_context(e, additional_context, logger)


def demonstrate_configuration_exceptions():
    """Demonstrate configuration exception handling."""
    print("\n=== Configuration Exceptions ===")
    
    try:
        # Simulate configuration error
        raise ConfigurationException(
            "Invalid database configuration",
            config_key="database_password",
            config_value="secret123"  # This will be sanitized
        )
    except ConfigurationException as e:
        print(f"Configuration error: {e}")
        print(f"Config value sanitized: {e.details['config_value'] == '[REDACTED]'}")


@handle_database_retry("example_database_operation", max_retries=3, base_delay=0.1)
async def example_database_operation(should_fail: bool = False):
    """Example database operation with retry decorator."""
    if should_fail:
        raise DatabaseException(
            "Simulated database error",
            retry_count=0,
            max_retries=3
        )
    return {"status": "success", "data": "operation completed"}


async def demonstrate_retry_decorator():
    """Demonstrate the database retry decorator."""
    print("\n=== Database Retry Decorator ===")
    
    # Successful operation
    result = await example_database_operation(should_fail=False)
    print(f"Successful operation: {result}")
    
    # Operation that will retry and eventually fail
    try:
        await example_database_operation(should_fail=True)
    except DatabaseException as e:
        print(f"Operation failed after retries: {e}")
        print(f"Final retry count: {e.retry_count}")


def demonstrate_error_response_creation():
    """Demonstrate creating standardized error responses."""
    print("\n=== Error Response Creation ===")
    
    # Create various types of exceptions
    exceptions = [
        VetCoreException("Generic error", error_code="GENERIC_ERROR"),
        ValidationException("Invalid input", field="email", value="invalid-email"),
        DatabaseException("Connection timeout", retry_count=2, max_retries=3),
        BusinessRuleException("Rule violation", rule_name="age_limit", context={"age": 150})
    ]
    
    for exc in exceptions:
        # Basic error response
        basic_response = create_error_response(exc)
        print(f"\n{exc.__class__.__name__} basic response:")
        print(f"  Success: {basic_response['success']}")
        print(f"  Error type: {basic_response['error']['type']}")
        print(f"  Error code: {basic_response['error']['code']}")
        
        # Debug response
        debug_response = create_error_response(exc, include_debug=True)
        if 'debug' in debug_response:
            print(f"  Debug info: {list(debug_response['debug'].keys())}")


async def main():
    """Run all demonstration examples."""
    print("Vet Core Package - Comprehensive Exception Handling Examples")
    print("=" * 60)
    
    demonstrate_basic_exceptions()
    demonstrate_database_exceptions()
    demonstrate_validation_error_formatting()
    demonstrate_business_rule_exceptions()
    demonstrate_configuration_exceptions()
    await demonstrate_retry_decorator()
    demonstrate_error_response_creation()
    
    print("\n" + "=" * 60)
    print("All exception handling examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())