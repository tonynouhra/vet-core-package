"""
Validation and data processing utilities for veterinary operations.

This module provides common validation patterns, data sanitization functions,
custom validation decorators, and error message standardization utilities.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

# Type variable for generic validation functions
T = TypeVar("T")


class ValidationError(Exception):
    """Custom validation error with structured error information."""

    def __init__(
        self, message: str, field: Optional[str] = None, code: Optional[str] = None
    ):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary format."""
        return {"message": self.message, "field": self.field, "code": self.code}


class ValidationResult(Generic[T]):
    """Result of a validation operation."""

    def __init__(
        self, value: Optional[T] = None, errors: Optional[List[ValidationError]] = None
    ):
        self.value = value
        self.errors = errors or []
        self.is_valid = len(self.errors) == 0

    def add_error(self, error: ValidationError) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False


# Email validation patterns
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Phone number patterns (supports various formats)
PHONE_PATTERNS = {
    "us": re.compile(
        r"^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$"
    ),
    "international": re.compile(r"^\+?[1-9]\d{1,14}$"),
}

# License number patterns for veterinarians
LICENSE_PATTERNS = {
    "us_general": re.compile(r"^[A-Z]{2}\d{4,8}$"),
    "alphanumeric": re.compile(r"^[A-Z0-9]{6,12}$"),
}


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string by normalizing unicode and trimming whitespace.

    Args:
        value: The string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    # Normalize unicode characters
    normalized = unicodedata.normalize("NFKC", value)

    # Strip whitespace and collapse multiple spaces
    sanitized = re.sub(r"\s+", " ", normalized.strip())

    # Truncate if necessary
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()

    return sanitized


def sanitize_name(name: str) -> str:
    """
    Sanitize a person or pet name.

    Args:
        name: The name to sanitize

    Returns:
        Sanitized name
    """
    sanitized = sanitize_string(name, max_length=100)

    # Remove any non-letter characters except spaces, hyphens, and apostrophes
    sanitized = re.sub(r"[^a-zA-Z\s\-']", "", sanitized)

    # Capitalize first letter of each word
    return " ".join(word.capitalize() for word in sanitized.split())


def validate_email(email: str) -> ValidationResult[str]:
    """
    Validate an email address.

    Args:
        email: The email to validate

    Returns:
        ValidationResult with the sanitized email or errors
    """
    result = ValidationResult[str]()

    if not email:
        result.add_error(ValidationError("Email is required", "email", "required"))
        return result

    # Sanitize the email
    sanitized_email = sanitize_string(email).lower()

    # Validate format
    if not EMAIL_PATTERN.match(sanitized_email):
        result.add_error(
            ValidationError("Invalid email format", "email", "invalid_format")
        )
        return result

    # Check length
    if len(sanitized_email) > 254:
        result.add_error(ValidationError("Email is too long", "email", "too_long"))
        return result

    result.value = sanitized_email
    return result


def validate_phone(phone: str, country: str = "us") -> ValidationResult[str]:
    """
    Validate and format a phone number.

    Args:
        phone: The phone number to validate
        country: Country code for validation pattern

    Returns:
        ValidationResult with the formatted phone or errors
    """
    result = ValidationResult[str]()

    if not phone:
        result.add_error(
            ValidationError("Phone number is required", "phone", "required")
        )
        return result

    # Remove all non-digit characters for processing
    digits_only = re.sub(r"\D", "", phone)

    # Validate using appropriate pattern
    pattern = PHONE_PATTERNS.get(country, PHONE_PATTERNS["us"])

    if not pattern.match(phone):
        result.add_error(
            ValidationError("Invalid phone number format", "phone", "invalid_format")
        )
        return result

    # Format US phone numbers consistently
    if country == "us" and len(digits_only) >= 10:
        if len(digits_only) == 11 and digits_only[0] == "1":
            digits_only = digits_only[1:]
        if len(digits_only) == 10:
            formatted = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            result.value = formatted
        else:
            result.add_error(
                ValidationError("Invalid US phone number", "phone", "invalid_format")
            )
    else:
        result.value = phone

    return result


def validate_weight(
    weight: Union[str, float, Decimal], unit: str = "lbs"
) -> ValidationResult[Decimal]:
    """
    Validate a pet's weight.

    Args:
        weight: The weight value
        unit: Unit of measurement ('lbs' or 'kg')

    Returns:
        ValidationResult with the weight as Decimal or errors
    """
    result = ValidationResult[Decimal]()

    try:
        weight_decimal = Decimal(str(weight))
    except (InvalidOperation, ValueError):
        result.add_error(
            ValidationError("Weight must be a valid number", "weight", "invalid_number")
        )
        return result

    # Validate range based on unit
    if unit == "lbs":
        min_weight, max_weight = Decimal("0.1"), Decimal("500")
    elif unit == "kg":
        min_weight, max_weight = Decimal("0.05"), Decimal("227")  # ~500 lbs
    else:
        result.add_error(
            ValidationError("Invalid weight unit", "weight", "invalid_unit")
        )
        return result

    if weight_decimal < min_weight:
        result.add_error(
            ValidationError(
                f"Weight must be at least {min_weight} {unit}", "weight", "too_low"
            )
        )
        return result

    if weight_decimal > max_weight:
        result.add_error(
            ValidationError(
                f"Weight cannot exceed {max_weight} {unit}", "weight", "too_high"
            )
        )
        return result

    result.value = weight_decimal
    return result


def validate_license_number(
    license_number: str, pattern_type: str = "us_general"
) -> ValidationResult[str]:
    """
    Validate a veterinarian license number.

    Args:
        license_number: The license number to validate
        pattern_type: Type of pattern to use for validation

    Returns:
        ValidationResult with the sanitized license number or errors
    """
    result = ValidationResult[str]()

    if not license_number:
        result.add_error(
            ValidationError("License number is required", "license_number", "required")
        )
        return result

    # Sanitize and uppercase
    sanitized = (
        sanitize_string(license_number).upper().replace(" ", "").replace("-", "")
    )

    # Validate pattern
    pattern = LICENSE_PATTERNS.get(pattern_type, LICENSE_PATTERNS["us_general"])

    if not pattern.match(sanitized):
        result.add_error(
            ValidationError(
                "Invalid license number format", "license_number", "invalid_format"
            )
        )
        return result

    result.value = sanitized
    return result


def validate_age_range(
    birth_date: date, min_age_days: int = 0, max_age_years: int = 30
) -> ValidationResult[date]:
    """
    Validate that a birth date falls within reasonable age ranges for pets.

    Args:
        birth_date: The birth date to validate
        min_age_days: Minimum age in days
        max_age_years: Maximum age in years

    Returns:
        ValidationResult with the birth date or errors
    """
    result = ValidationResult[date]()

    if not birth_date:
        result.add_error(
            ValidationError("Birth date is required", "birth_date", "required")
        )
        return result

    today = date.today()

    # Check if birth date is in the future
    if birth_date > today:
        result.add_error(
            ValidationError(
                "Birth date cannot be in the future", "birth_date", "future_date"
            )
        )
        return result

    # Check minimum age
    min_date = today - timedelta(days=min_age_days)
    if birth_date > min_date:
        result.add_error(
            ValidationError(
                f"Pet must be at least {min_age_days} days old",
                "birth_date",
                "too_young",
            )
        )
        return result

    # Check maximum age
    max_date = today.replace(year=today.year - max_age_years)
    if birth_date < max_date:
        result.add_error(
            ValidationError(
                f"Pet age cannot exceed {max_age_years} years", "birth_date", "too_old"
            )
        )
        return result

    result.value = birth_date
    return result


def validate_species_breed(
    species: str, breed: str
) -> ValidationResult[Dict[str, str]]:
    """
    Validate species and breed combination.

    Args:
        species: The pet species
        breed: The pet breed

    Returns:
        ValidationResult with sanitized species and breed or errors
    """
    result = ValidationResult[Dict[str, str]]()

    if not species:
        result.add_error(ValidationError("Species is required", "species", "required"))

    if not breed:
        result.add_error(ValidationError("Breed is required", "breed", "required"))

    if result.errors:
        return result

    # Sanitize values
    sanitized_species = sanitize_name(species)
    sanitized_breed = sanitize_name(breed)

    # Basic validation - could be extended with breed databases
    valid_species = [
        "Dog",
        "Cat",
        "Bird",
        "Rabbit",
        "Hamster",
        "Guinea Pig",
        "Ferret",
        "Reptile",
        "Fish",
        "Other",
    ]

    if sanitized_species not in valid_species:
        # Allow custom species but warn
        pass

    result.value = {"species": sanitized_species, "breed": sanitized_breed}
    return result


# Validation decorators
def validate_required(field_name: str) -> Callable:
    """Decorator to validate that a field is required."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # This is a placeholder for field validation logic
            # In practice, this would be used with Pydantic or similar
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_length(min_length: int = 0, max_length: Optional[int] = None) -> Callable:
    """Decorator to validate string length."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(value: str, *args: Any, **kwargs: Any) -> Any:
            if len(value) < min_length:
                raise ValidationError(
                    f"Value must be at least {min_length} characters", code="too_short"
                )
            if max_length and len(value) > max_length:
                raise ValidationError(
                    f"Value cannot exceed {max_length} characters", code="too_long"
                )
            return func(value, *args, **kwargs)

        return wrapper
    return decorator


def validate_range(
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
) -> Callable:
    """Decorator to validate numeric ranges."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(value: Union[int, float], *args: Any, **kwargs: Any) -> Any:
            if min_value is not None and value < min_value:
                raise ValidationError(
                    f"Value must be at least {min_value}", code="too_low"
                )
            if max_value is not None and value > max_value:
                raise ValidationError(
                    f"Value cannot exceed {max_value}", code="too_high"
                )
            return func(value, *args, **kwargs)

        return wrapper

    return decorator


class ErrorMessageFormatter:
    """Utility class for standardizing error messages."""

    @staticmethod
    def format_validation_errors(errors: List[ValidationError]) -> Dict[str, Any]:
        """
        Format a list of validation errors into a standardized response.

        Args:
            errors: List of ValidationError objects

        Returns:
            Formatted error response
        """
        formatted_errors: Dict[str, List[Dict[str, str]]] = {}
        general_errors: List[Dict[str, str]] = []

        for error in errors:
            if error.field:
                if error.field not in formatted_errors:
                    formatted_errors[error.field] = []
                formatted_errors[error.field].append(
                    {"message": error.message, "code": error.code or ""}
                )
            else:
                general_errors.append(
                    {"message": error.message, "code": error.code or ""}
                )

        result = {"success": False, "errors": formatted_errors}

        if general_errors:
            result["general_errors"] = general_errors

        return result

    @staticmethod
    def format_success_response(
        data: Any, message: str = "Operation successful"
    ) -> Dict[str, Any]:
        """
        Format a successful response.

        Args:
            data: The response data
            message: Success message

        Returns:
            Formatted success response
        """
        return {"success": True, "message": message, "data": data}


def batch_validate(
    validators: Dict[str, Callable], data: Dict[str, Any]
) -> ValidationResult[Dict[str, Any]]:
    """
    Validate multiple fields using their respective validators.

    Args:
        validators: Dictionary mapping field names to validator functions
        data: Dictionary of data to validate

    Returns:
        ValidationResult with validated data or accumulated errors
    """
    result = ValidationResult[Dict[str, Any]]()
    validated_data = {}

    for field_name, validator in validators.items():
        if field_name in data:
            try:
                field_result = validator(data[field_name])
                if isinstance(field_result, ValidationResult):
                    if field_result.is_valid:
                        validated_data[field_name] = field_result.value
                    else:
                        result.errors.extend(field_result.errors)
                else:
                    validated_data[field_name] = field_result
            except ValidationError as e:
                e.field = field_name
                result.add_error(e)
            except Exception as e:
                result.add_error(
                    ValidationError(str(e), field_name, "validation_error")
                )

    if result.is_valid:
        result.value = validated_data

    return result
