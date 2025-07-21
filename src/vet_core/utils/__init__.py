"""
Utility functions and helper modules.

This module provides common utility functions for datetime handling,
validation, configuration management, and other shared functionality.
"""

from .datetime_utils import (
    DayOfWeek,
    BusinessHours,
    get_current_utc,
    get_current_local,
    convert_timezone,
    to_utc,
    from_utc,
    is_business_hours,
    get_next_business_day,
    get_available_appointment_slots,
    calculate_pet_age,
    format_pet_age,
    get_pet_age_category,
    is_appointment_time_valid,
    round_to_nearest_slot,
)

from .validation import (
    ValidationError,
    ValidationResult,
    sanitize_string,
    sanitize_name,
    validate_email,
    validate_phone,
    validate_weight,
    validate_license_number,
    validate_age_range,
    validate_species_breed,
    validate_required,
    validate_length,
    validate_range,
    ErrorMessageFormatter,
    batch_validate,
)

from .config import (
    ConfigError,
    LogLevel,
    DatabaseConfig,
    FeatureFlag,
    EnvironmentConfig,
    DatabaseURLValidator,
    LoggingConfigurator,
    FeatureFlagManager,
    get_feature_flag_manager,
    is_feature_enabled,
)

__all__ = [
    # DateTime utilities
    "DayOfWeek",
    "BusinessHours",
    "get_current_utc",
    "get_current_local",
    "convert_timezone",
    "to_utc",
    "from_utc",
    "is_business_hours",
    "get_next_business_day",
    "get_available_appointment_slots",
    "calculate_pet_age",
    "format_pet_age",
    "get_pet_age_category",
    "is_appointment_time_valid",
    "round_to_nearest_slot",
    # Validation helpers
    "ValidationError",
    "ValidationResult",
    "sanitize_string",
    "sanitize_name",
    "validate_email",
    "validate_phone",
    "validate_weight",
    "validate_license_number",
    "validate_age_range",
    "validate_species_breed",
    "validate_required",
    "validate_length",
    "validate_range",
    "ErrorMessageFormatter",
    "batch_validate",
    # Configuration utilities
    "ConfigError",
    "LogLevel",
    "DatabaseConfig",
    "FeatureFlag",
    "EnvironmentConfig",
    "DatabaseURLValidator",
    "LoggingConfigurator",
    "FeatureFlagManager",
    "get_feature_flag_manager",
    "is_feature_enabled",
]