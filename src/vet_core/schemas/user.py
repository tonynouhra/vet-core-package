"""
User Pydantic schemas for API validation and serialization.

This module contains Pydantic schemas for User model validation,
including create, update, and response schemas with role-based restrictions.
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from ..models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Base User schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,  # Can create from SQLAlchemy models
        use_enum_values=True,  # Serialize enums as values
        validate_assignment=True,  # Validate on assignment
        str_strip_whitespace=True,  # Validate on field assignment
    )

    email: EmailStr = Field(..., description="User's email address", max_length=255)
    first_name: str = Field(
        ..., description="User's first name", min_length=1, max_length=100
    )
    last_name: str = Field(
        ..., description="User's last name", min_length=1, max_length=100
    )
    phone_number: Optional[str] = Field(
        None, description="User's phone number", max_length=20
    )
    avatar_url: Optional[str] = Field(
        None, description="URL to user's avatar image", max_length=500
    )
    bio: Optional[str] = Field(
        None, description="User's biography or description", max_length=1000
    )
    address_line1: Optional[str] = Field(
        None, description="Primary address line", max_length=255
    )
    address_line2: Optional[str] = Field(
        None, description="Secondary address line", max_length=255
    )
    city: Optional[str] = Field(None, description="City", max_length=100)
    state: Optional[str] = Field(None, description="State or province", max_length=100)
    postal_code: Optional[str] = Field(
        None, description="Postal or ZIP code", max_length=20
    )
    country: Optional[str] = Field("US", description="Country code", max_length=100)
    email_notifications: bool = Field(
        True, description="Whether user wants to receive email notifications"
    )
    sms_notifications: bool = Field(
        False, description="Whether user wants to receive SMS notifications"
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate email format and domain restrictions."""
        if not v:
            raise ValueError("Email is required")

        # Additional email validation beyond EmailStr
        if len(v) > 255:
            raise ValueError("Email address too long")

        # Check for common invalid patterns
        if ".." in v:
            raise ValueError("Email cannot contain consecutive dots")

        if v.startswith(".") or v.endswith("."):
            raise ValueError("Email cannot start or end with a dot")

        return v.lower()

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format."""
        if v is None:
            return v

        # Remove all non-digit characters for validation
        digits_only = re.sub(r"\D", "", v)

        # Check if it's a valid length (10-15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits")

        # Format phone number consistently
        if len(digits_only) == 10:
            # US format: (123) 456-7890
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        if len(digits_only) == 11 and digits_only.startswith("1"):
            # US format with country code: +1 (123) 456-7890
            return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        # International format: +XX XXXXXXXXX
        return f"+{digits_only}"

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_fields(cls, v: str) -> str:
        """Validate name fields."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", v):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and apostrophes"
            )

        # Capitalize first letter of each word
        return " ".join(word.capitalize() for word in v.split())

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate postal code format."""
        if v is None:
            return v

        # Remove spaces and convert to uppercase
        v = v.replace(" ", "").upper()

        # Basic validation - alphanumeric characters only
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("Postal code can only contain letters and numbers")

        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code."""
        if v is None:
            return "US"

        # Convert to uppercase for consistency
        v = v.upper()

        # Basic validation - should be 2-3 character country code
        if not re.match(r"^[A-Z]{2,3}$", v):
            raise ValueError("Country must be a valid 2-3 character country code")

        return v


class UserCreate(UserBase):
    """Schema for creating a new user."""

    clerk_user_id: str = Field(
        ...,
        description="Unique identifier from Clerk authentication service",
        max_length=255,
    )
    role: UserRole = Field(
        UserRole.PET_OWNER, description="User's role in the platform"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        None, description="User preferences and settings"
    )

    @field_validator("clerk_user_id")
    @classmethod
    def validate_clerk_user_id(cls, v: str) -> str:
        """Validate Clerk user ID format."""
        if not v or not v.strip():
            raise ValueError("Clerk user ID is required")

        # Basic format validation for Clerk user IDs
        if not re.match(r"^user_[a-zA-Z0-9]+$", v):
            raise ValueError("Invalid Clerk user ID format")

        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        """Validate user role."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                return UserRole(v)
            except ValueError:
                raise ValueError(
                    f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
                )

        # Handle enum values
        if not isinstance(v, UserRole):
            raise ValueError(
                f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
            )

        return v

    @field_validator("preferences")
    @classmethod
    def validate_preferences(
        cls, v: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate user preferences."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Preferences must be a dictionary")

        # Validate preference keys and values
        allowed_keys = {
            "theme",
            "language",
            "timezone",
            "date_format",
            "time_format",
            "notification_frequency",
            "dashboard_layout",
            "default_view",
        }

        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError("Preference keys must be strings")
            if key not in allowed_keys:
                raise ValueError(f"Invalid preference key: {key}")

        return v


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    first_name: Optional[str] = Field(
        None, description="User's first name", min_length=1, max_length=100
    )
    last_name: Optional[str] = Field(
        None, description="User's last name", min_length=1, max_length=100
    )
    phone_number: Optional[str] = Field(
        None, description="User's phone number", max_length=20
    )
    avatar_url: Optional[str] = Field(
        None, description="URL to user's avatar image", max_length=500
    )
    bio: Optional[str] = Field(
        None, description="User's biography or description", max_length=1000
    )
    address_line1: Optional[str] = Field(
        None, description="Primary address line", max_length=255
    )
    address_line2: Optional[str] = Field(
        None, description="Secondary address line", max_length=255
    )
    city: Optional[str] = Field(None, description="City", max_length=100)
    state: Optional[str] = Field(None, description="State or province", max_length=100)
    postal_code: Optional[str] = Field(
        None, description="Postal or ZIP code", max_length=20
    )
    country: Optional[str] = Field(None, description="Country code", max_length=100)
    email_notifications: Optional[bool] = Field(
        None, description="Whether user wants to receive email notifications"
    )
    sms_notifications: Optional[bool] = Field(
        None, description="Whether user wants to receive SMS notifications"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        None, description="User preferences and settings"
    )

    # Use the same validators as UserBase for applicable fields
    _validate_phone_number = field_validator("phone_number")(
        UserBase.validate_phone_number
    )
    _validate_name_fields = field_validator("first_name", "last_name")(
        UserBase.validate_name_fields
    )
    _validate_postal_code = field_validator("postal_code")(
        UserBase.validate_postal_code
    )
    _validate_country = field_validator("country")(UserBase.validate_country)
    _validate_preferences = field_validator("preferences")(
        UserCreate.validate_preferences
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UserUpdate":
        """Ensure at least one field is provided for update."""
        field_values = [
            self.first_name,
            self.last_name,
            self.phone_number,
            self.avatar_url,
            self.bio,
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
            self.email_notifications,
            self.sms_notifications,
            self.preferences,
        ]
        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self


class UserResponse(BaseModel):
    """Schema for user response data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role in the platform")
    status: UserStatus = Field(..., description="User's account status")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    avatar_url: Optional[str] = Field(None, description="URL to user's avatar image")
    bio: Optional[str] = Field(None, description="User's biography")
    address_line1: Optional[str] = Field(None, description="Primary address line")
    address_line2: Optional[str] = Field(None, description="Secondary address line")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal or ZIP code")
    country: Optional[str] = Field(None, description="Country code")
    email_notifications: bool = Field(..., description="Email notification preference")
    sms_notifications: bool = Field(..., description="SMS notification preference")
    email_verified: bool = Field(..., description="Whether email is verified")
    phone_verified: bool = Field(..., description="Whether phone is verified")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserAdminResponse(UserResponse):
    """Extended user response schema for admin users with sensitive fields."""

    clerk_user_id: str = Field(..., description="Clerk authentication ID")
    terms_accepted_at: Optional[str] = Field(
        None, description="Terms acceptance timestamp"
    )
    privacy_accepted_at: Optional[str] = Field(
        None, description="Privacy policy acceptance timestamp"
    )


class UserListResponse(BaseModel):
    """Schema for paginated user list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role")
    status: UserStatus = Field(..., description="User's status")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    created_at: datetime = Field(..., description="Creation timestamp")


class UserRoleUpdate(BaseModel):
    """Schema for updating user role (admin only)."""

    model_config = ConfigDict(use_enum_values=True)

    role: UserRole = Field(..., description="New user role")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        """Validate user role."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                return UserRole(v)
            except ValueError:
                raise ValueError(
                    f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
                )

        # Handle enum values
        if not isinstance(v, UserRole):
            raise ValueError(
                f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
            )
        return v


class UserStatusUpdate(BaseModel):
    """Schema for updating user status (admin only)."""

    model_config = ConfigDict(use_enum_values=True)

    status: UserStatus = Field(..., description="New user status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: UserStatus) -> UserStatus:
        """Validate user status."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                return UserStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status. Must be one of: {[status.value for status in UserStatus]}"
                )

        # Handle enum values
        if not isinstance(v, UserStatus):
            raise ValueError(
                f"Invalid status. Must be one of: {[status.value for status in UserStatus]}"
            )
        return v


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    model_config = ConfigDict(validate_assignment=True)

    preferences: Dict[str, Any] = Field(..., description="User preferences to update")

    @field_validator("preferences")
    @classmethod
    def validate_preferences(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user preferences."""
        if not isinstance(v, dict):
            raise ValueError("Preferences must be a dictionary")

        # Validate preference keys
        allowed_keys = {
            "theme",
            "language",
            "timezone",
            "date_format",
            "time_format",
            "notification_frequency",
            "dashboard_layout",
            "default_view",
        }

        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError("Preference keys must be strings")
            if key not in allowed_keys:
                raise ValueError(f"Invalid preference key: {key}")

        return v


# Role-specific schemas for different user types
class PetOwnerCreate(UserCreate):
    """Schema for creating pet owner accounts."""

    role: UserRole = Field(
        UserRole.PET_OWNER, description="Role fixed as pet owner", frozen=True
    )


class VeterinarianCreate(UserCreate):
    """Schema for creating veterinarian accounts."""

    role: UserRole = Field(
        UserRole.VETERINARIAN, description="Role fixed as veterinarian", frozen=True
    )


class VetTechCreate(UserCreate):
    """Schema for creating vet tech accounts."""

    role: UserRole = Field(
        UserRole.VET_TECH, description="Role fixed as vet tech", frozen=True
    )


class ClinicAdminCreate(UserCreate):
    """Schema for creating clinic admin accounts."""

    role: UserRole = Field(
        UserRole.CLINIC_ADMIN, description="Role fixed as clinic admin", frozen=True
    )


class PlatformAdminCreate(UserCreate):
    """Schema for creating platform admin accounts."""

    role: UserRole = Field(
        UserRole.PLATFORM_ADMIN, description="Role fixed as platform admin", frozen=True
    )
