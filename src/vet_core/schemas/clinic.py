"""
Clinic Pydantic schemas for API validation and serialization.

This module contains Pydantic schemas for Clinic model validation,
including create, update, and response schemas with location and operating hours validation.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from ..models.clinic import ClinicStatus, ClinicType


class OperatingHoursSchema(BaseModel):
    """Schema for daily operating hours."""

    model_config = ConfigDict(from_attributes=True)

    is_open: bool = Field(..., description="Whether the clinic is open on this day")
    open_time: Optional[str] = Field(None, description="Opening time in HH:MM format")
    close_time: Optional[str] = Field(None, description="Closing time in HH:MM format")
    lunch_break: Optional[Dict[str, str]] = Field(
        None, description="Lunch break with 'start' and 'end' times"
    )

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format."""
        if v is None:
            return v

        # Validate HH:MM format
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")

        return v

    @field_validator("lunch_break")
    @classmethod
    def validate_lunch_break(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Validate lunch break format."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Lunch break must be a dictionary")

        required_keys = {"start", "end"}
        if not required_keys.issubset(v.keys()):
            raise ValueError("Lunch break must have 'start' and 'end' times")

        # Validate time formats
        for key in required_keys:
            time_val = v[key]
            if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_val):
                raise ValueError(f"Lunch break {key} time must be in HH:MM format")

        return v

    @model_validator(mode="after")
    def validate_operating_hours_consistency(self):
        """Validate operating hours consistency."""
        if self.is_open:
            if not self.open_time or not self.close_time:
                raise ValueError(
                    "Open and close times are required when clinic is open"
                )

            # Convert to minutes for comparison
            def time_to_minutes(time_str: str) -> int:
                hours, minutes = map(int, time_str.split(":"))
                return hours * 60 + minutes

            open_minutes = time_to_minutes(self.open_time)
            close_minutes = time_to_minutes(self.close_time)

            if close_minutes <= open_minutes:
                raise ValueError("Close time must be after open time")

            # Validate lunch break is within operating hours
            if self.lunch_break:
                lunch_start = time_to_minutes(self.lunch_break["start"])
                lunch_end = time_to_minutes(self.lunch_break["end"])

                if lunch_start >= lunch_end:
                    raise ValueError("Lunch break end time must be after start time")

                if lunch_start < open_minutes or lunch_end > close_minutes:
                    raise ValueError("Lunch break must be within operating hours")

        return self


class ClinicBase(BaseModel):
    """Base Clinic schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    name: str = Field(..., description="Clinic name", min_length=1, max_length=200)
    type: ClinicType = Field(
        ClinicType.GENERAL_PRACTICE, description="Type of veterinary clinic"
    )
    phone_number: str = Field(..., description="Primary phone number", max_length=20)
    email: Optional[EmailStr] = Field(None, description="Primary email address")
    website_url: Optional[str] = Field(
        None, description="Clinic website URL", max_length=500
    )
    address_line1: str = Field(
        ..., description="Primary address line", min_length=1, max_length=255
    )
    address_line2: Optional[str] = Field(
        None, description="Secondary address line", max_length=255
    )
    city: str = Field(..., description="City", min_length=1, max_length=100)
    state: str = Field(
        ..., description="State or province", min_length=1, max_length=100
    )
    postal_code: str = Field(
        ..., description="Postal or ZIP code", min_length=1, max_length=20
    )
    country: str = Field("US", description="Country code", max_length=100)
    latitude: Optional[float] = Field(
        None, description="Latitude coordinate", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, description="Longitude coordinate", ge=-180, le=180
    )
    timezone: Optional[str] = Field(
        None, description="Timezone identifier", max_length=50
    )
    services_offered: Optional[List[str]] = Field(
        None, description="List of services offered by the clinic"
    )
    specialties: Optional[List[str]] = Field(
        None, description="List of medical specialties available"
    )
    accepts_new_patients: bool = Field(
        True, description="Whether the clinic is accepting new patients"
    )
    accepts_emergencies: bool = Field(
        False, description="Whether the clinic handles emergency cases"
    )
    accepts_walk_ins: bool = Field(
        False, description="Whether the clinic accepts walk-in appointments"
    )
    description: Optional[str] = Field(
        None, description="Description of the clinic and its services"
    )
    facility_features: Optional[List[str]] = Field(
        None, description="List of facility features"
    )
    equipment_available: Optional[List[str]] = Field(
        None, description="List of medical equipment available"
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum number of appointments per day", gt=0
    )
    number_of_exam_rooms: Optional[int] = Field(
        None, description="Number of examination rooms", gt=0
    )
    number_of_surgery_rooms: Optional[int] = Field(
        None, description="Number of surgery rooms", ge=0
    )
    insurance_accepted: Optional[List[str]] = Field(
        None, description="List of accepted insurance providers"
    )
    payment_methods: Optional[List[str]] = Field(
        None, description="List of accepted payment methods"
    )
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact phone number", max_length=20
    )
    after_hours_instructions: Optional[str] = Field(
        None, description="Instructions for after-hours emergencies"
    )
    logo_url: Optional[str] = Field(
        None, description="URL to clinic logo image", max_length=500
    )
    photos: Optional[List[str]] = Field(
        None, description="Array of photo URLs for the clinic"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate clinic name."""
        if not v or not v.strip():
            raise ValueError("Clinic name is required")

        # Allow letters, numbers, spaces, and common punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-'.,()&]+$", v):
            raise ValueError("Clinic name contains invalid characters")

        return v.strip()

    @field_validator("phone_number", "emergency_contact_number")
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

    @field_validator("website_url", "logo_url")
    @classmethod
    def validate_url_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Basic URL validation
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v, re.IGNORECASE):
            raise ValueError("Invalid URL format")

        return v

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        """Validate postal code format."""
        # Remove spaces and convert to uppercase
        v = v.replace(" ", "").upper()

        # Basic validation - alphanumeric characters only
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("Postal code can only contain letters and numbers")

        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country code."""
        # Convert to uppercase for consistency
        v = v.upper()

        # Basic validation - should be 2-3 character country code
        if not re.match(r"^[A-Z]{2,3}$", v):
            raise ValueError("Country must be a valid 2-3 character country code")

        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone identifier."""
        if v is None:
            return v

        # Basic timezone format validation
        if not re.match(r"^[A-Za-z_]+/[A-Za-z_]+$", v):
            raise ValueError(
                "Timezone must be in format 'Region/City' (e.g., 'America/New_York')"
            )

        return v

    @field_validator(
        "services_offered",
        "specialties",
        "facility_features",
        "equipment_available",
        "insurance_accepted",
        "payment_methods",
    )
    @classmethod
    def validate_string_lists(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate string lists."""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("Field must be a list of strings")

        # Validate each item
        validated_items = []
        for item in v:
            if not isinstance(item, str):
                raise ValueError("All items must be strings")

            item = item.strip()
            if item:  # Only add non-empty items
                validated_items.append(item)

        # Remove duplicates while preserving order
        seen = set()
        unique_items = []
        for item in validated_items:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique_items.append(item)

        return unique_items if unique_items else None

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate photo URLs."""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("Photos must be a list of URLs")

        if len(v) > 20:  # Reasonable limit
            raise ValueError("Maximum 20 photos allowed")

        validated_urls = []
        for url in v:
            if not isinstance(url, str):
                raise ValueError("All photo URLs must be strings")

            url = url.strip()
            if url:
                # Basic URL validation
                url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
                if not re.match(url_pattern, url, re.IGNORECASE):
                    raise ValueError(f"Invalid photo URL format: {url}")
                validated_urls.append(url)

        return validated_urls if validated_urls else None

    @field_validator("description", "after_hours_instructions")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate text fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Check for reasonable length
            if len(v) > 5000:
                raise ValueError("Text field is too long (maximum 5000 characters)")

        return v

    @model_validator(mode="after")
    def validate_coordinates_consistency(self):
        """Validate that both latitude and longitude are provided together."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both latitude and longitude must be provided together")
        return self


class ClinicCreate(ClinicBase):
    """Schema for creating a new clinic."""

    license_number: Optional[str] = Field(
        None, description="Veterinary clinic license number", max_length=100
    )
    status: ClinicStatus = Field(
        ClinicStatus.ACTIVE, description="Initial clinic status"
    )
    operating_hours: Optional[Dict[str, OperatingHoursSchema]] = Field(
        None, description="Operating hours by day of week"
    )

    @field_validator("license_number")
    @classmethod
    def validate_license_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate license number."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic alphanumeric validation
            if not re.match(r"^[A-Z0-9\-]+$", v.upper()):
                raise ValueError(
                    "License number can only contain letters, numbers, and hyphens"
                )

        return v.upper() if v else None

    @field_validator("operating_hours")
    @classmethod
    def validate_operating_hours(
        cls, v: Optional[Dict[str, OperatingHoursSchema]]
    ) -> Optional[Dict[str, OperatingHoursSchema]]:
        """Validate operating hours."""
        if v is None:
            return v

        valid_days = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }

        for day, hours in v.items():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day of week: {day}")

            if not isinstance(hours, OperatingHoursSchema):
                raise ValueError(
                    f"Operating hours for {day} must be an OperatingHoursSchema"
                )

        return v


class ClinicUpdate(BaseModel):
    """Schema for updating an existing clinic."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    name: Optional[str] = Field(
        None, description="Clinic name", min_length=1, max_length=200
    )
    license_number: Optional[str] = Field(
        None, description="Veterinary clinic license number", max_length=100
    )
    type: Optional[ClinicType] = Field(None, description="Type of veterinary clinic")
    status: Optional[ClinicStatus] = Field(None, description="Clinic status")
    phone_number: Optional[str] = Field(
        None, description="Primary phone number", max_length=20
    )
    email: Optional[EmailStr] = Field(None, description="Primary email address")
    website_url: Optional[str] = Field(
        None, description="Clinic website URL", max_length=500
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
    latitude: Optional[float] = Field(
        None, description="Latitude coordinate", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, description="Longitude coordinate", ge=-180, le=180
    )
    timezone: Optional[str] = Field(
        None, description="Timezone identifier", max_length=50
    )
    operating_hours: Optional[Dict[str, OperatingHoursSchema]] = Field(
        None, description="Operating hours by day of week"
    )
    services_offered: Optional[List[str]] = Field(
        None, description="List of services offered by the clinic"
    )
    specialties: Optional[List[str]] = Field(
        None, description="List of medical specialties available"
    )
    accepts_new_patients: Optional[bool] = Field(
        None, description="Whether the clinic is accepting new patients"
    )
    accepts_emergencies: Optional[bool] = Field(
        None, description="Whether the clinic handles emergency cases"
    )
    accepts_walk_ins: Optional[bool] = Field(
        None, description="Whether the clinic accepts walk-in appointments"
    )
    description: Optional[str] = Field(
        None, description="Description of the clinic and its services"
    )
    facility_features: Optional[List[str]] = Field(
        None, description="List of facility features"
    )
    equipment_available: Optional[List[str]] = Field(
        None, description="List of medical equipment available"
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum number of appointments per day", gt=0
    )
    number_of_exam_rooms: Optional[int] = Field(
        None, description="Number of examination rooms", gt=0
    )
    number_of_surgery_rooms: Optional[int] = Field(
        None, description="Number of surgery rooms", ge=0
    )
    insurance_accepted: Optional[List[str]] = Field(
        None, description="List of accepted insurance providers"
    )
    payment_methods: Optional[List[str]] = Field(
        None, description="List of accepted payment methods"
    )
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact phone number", max_length=20
    )
    after_hours_instructions: Optional[str] = Field(
        None, description="Instructions for after-hours emergencies"
    )
    logo_url: Optional[str] = Field(
        None, description="URL to clinic logo image", max_length=500
    )
    photos: Optional[List[str]] = Field(
        None, description="Array of photo URLs for the clinic"
    )

    # Use the same validators as ClinicBase for applicable fields
    _validate_name = field_validator("name")(ClinicBase.validate_name)
    _validate_phone_number = field_validator(
        "phone_number", "emergency_contact_number"
    )(ClinicBase.validate_phone_number)
    _validate_url_format = field_validator("website_url", "logo_url")(
        ClinicBase.validate_url_format
    )
    _validate_postal_code = field_validator("postal_code")(
        ClinicBase.validate_postal_code
    )
    _validate_country = field_validator("country")(ClinicBase.validate_country)
    _validate_timezone = field_validator("timezone")(ClinicBase.validate_timezone)
    _validate_string_lists = field_validator(
        "services_offered",
        "specialties",
        "facility_features",
        "equipment_available",
        "insurance_accepted",
        "payment_methods",
    )(ClinicBase.validate_string_lists)
    _validate_photos = field_validator("photos")(ClinicBase.validate_photos)
    _validate_text_fields = field_validator("description", "after_hours_instructions")(
        ClinicBase.validate_text_fields
    )
    _validate_license_number = field_validator("license_number")(
        ClinicCreate.validate_license_number
    )
    _validate_operating_hours = field_validator("operating_hours")(
        ClinicCreate.validate_operating_hours
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """Ensure at least one field is provided for update."""
        field_names = list(self.model_fields.keys())
        field_values = [getattr(self, name) for name in field_names]

        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self


class ClinicResponse(BaseModel):
    """Schema for clinic response data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

    id: UUID = Field(..., description="Clinic's unique identifier")
    name: str = Field(..., description="Clinic name")
    license_number: Optional[str] = Field(
        None, description="Veterinary clinic license number"
    )
    type: ClinicType = Field(..., description="Type of veterinary clinic")
    status: ClinicStatus = Field(..., description="Current operational status")
    phone_number: str = Field(..., description="Primary phone number")
    email: Optional[str] = Field(None, description="Primary email address")
    website_url: Optional[str] = Field(None, description="Clinic website URL")
    address_line1: str = Field(..., description="Primary address line")
    address_line2: Optional[str] = Field(None, description="Secondary address line")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State or province")
    postal_code: str = Field(..., description="Postal or ZIP code")
    country: str = Field(..., description="Country code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    timezone: Optional[str] = Field(None, description="Timezone identifier")
    operating_hours: Optional[Dict[str, Any]] = Field(
        None, description="Operating hours by day of week"
    )
    services_offered: Optional[List[str]] = Field(
        None, description="List of services offered"
    )
    specialties: Optional[List[str]] = Field(
        None, description="List of medical specialties"
    )
    accepts_new_patients: bool = Field(
        ..., description="Whether accepting new patients"
    )
    accepts_emergencies: bool = Field(
        ..., description="Whether handling emergency cases"
    )
    accepts_walk_ins: bool = Field(
        ..., description="Whether accepting walk-in appointments"
    )
    description: Optional[str] = Field(None, description="Clinic description")
    facility_features: Optional[List[str]] = Field(
        None, description="List of facility features"
    )
    equipment_available: Optional[List[str]] = Field(
        None, description="List of medical equipment"
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum daily appointments"
    )
    number_of_exam_rooms: Optional[int] = Field(
        None, description="Number of examination rooms"
    )
    number_of_surgery_rooms: Optional[int] = Field(
        None, description="Number of surgery rooms"
    )
    insurance_accepted: Optional[List[str]] = Field(
        None, description="Accepted insurance providers"
    )
    payment_methods: Optional[List[str]] = Field(
        None, description="Accepted payment methods"
    )
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact number"
    )
    after_hours_instructions: Optional[str] = Field(
        None, description="After-hours instructions"
    )
    logo_url: Optional[str] = Field(None, description="Clinic logo URL")
    photos: Optional[List[str]] = Field(None, description="Clinic photo URLs")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ClinicListResponse(BaseModel):
    """Schema for paginated clinic list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Clinic's unique identifier")
    name: str = Field(..., description="Clinic name")
    type: ClinicType = Field(..., description="Type of veterinary clinic")
    status: ClinicStatus = Field(..., description="Current operational status")
    phone_number: str = Field(..., description="Primary phone number")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State or province")
    accepts_new_patients: bool = Field(
        ..., description="Whether accepting new patients"
    )
    accepts_emergencies: bool = Field(
        ..., description="Whether handling emergency cases"
    )
    logo_url: Optional[str] = Field(None, description="Clinic logo URL")
    created_at: datetime = Field(..., description="Creation timestamp")


class ClinicStatusUpdate(BaseModel):
    """Schema for updating clinic status."""

    model_config = ConfigDict(use_enum_values=True)

    status: ClinicStatus = Field(..., description="New clinic status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: ClinicStatus) -> ClinicStatus:
        """Validate clinic status."""
        if v not in ClinicStatus:
            raise ValueError(
                f"Invalid status. Must be one of: {[status.value for status in ClinicStatus]}"
            )
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate reason."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 500:
                raise ValueError("Reason is too long (maximum 500 characters)")
        return v


class ClinicSearchFilters(BaseModel):
    """Schema for clinic search filters."""

    model_config = ConfigDict(validate_assignment=True)

    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    country: Optional[str] = Field(None, description="Filter by country")
    type: Optional[ClinicType] = Field(None, description="Filter by clinic type")
    accepts_new_patients: Optional[bool] = Field(
        None, description="Filter by new patient acceptance"
    )
    accepts_emergencies: Optional[bool] = Field(
        None, description="Filter by emergency services"
    )
    accepts_walk_ins: Optional[bool] = Field(
        None, description="Filter by walk-in acceptance"
    )
    services_offered: Optional[List[str]] = Field(
        None, description="Filter by services offered"
    )
    specialties: Optional[List[str]] = Field(None, description="Filter by specialties")
    latitude: Optional[float] = Field(
        None, description="Latitude for distance search", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, description="Longitude for distance search", ge=-180, le=180
    )
    radius_km: Optional[float] = Field(
        None, description="Search radius in kilometers", gt=0, le=100
    )

    @model_validator(mode="after")
    def validate_location_search(self):
        """Validate location search parameters."""
        location_fields = [self.latitude, self.longitude, self.radius_km]
        provided_count = sum(1 for field in location_fields if field is not None)

        if provided_count > 0 and provided_count != 3:
            raise ValueError(
                "For location search, latitude, longitude, and radius_km must all be provided"
            )

        return self


class ClinicOperatingHoursUpdate(BaseModel):
    """Schema for updating clinic operating hours."""

    model_config = ConfigDict(validate_assignment=True)

    operating_hours: Dict[str, OperatingHoursSchema] = Field(
        ..., description="Operating hours by day of week"
    )

    @field_validator("operating_hours")
    @classmethod
    def validate_operating_hours(
        cls, v: Dict[str, OperatingHoursSchema]
    ) -> Dict[str, OperatingHoursSchema]:
        """Validate operating hours."""
        valid_days = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }

        for day, hours in v.items():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day of week: {day}")

            if not isinstance(hours, OperatingHoursSchema):
                raise ValueError(
                    f"Operating hours for {day} must be an OperatingHoursSchema"
                )

        return v


class ClinicLocationUpdate(BaseModel):
    """Schema for updating clinic location information."""

    model_config = ConfigDict(validate_assignment=True)

    address_line1: str = Field(..., description="Primary address line", max_length=255)
    address_line2: Optional[str] = Field(
        None, description="Secondary address line", max_length=255
    )
    city: str = Field(..., description="City", max_length=100)
    state: str = Field(..., description="State or province", max_length=100)
    postal_code: str = Field(..., description="Postal or ZIP code", max_length=20)
    country: str = Field("US", description="Country code", max_length=100)
    latitude: Optional[float] = Field(
        None, description="Latitude coordinate", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, description="Longitude coordinate", ge=-180, le=180
    )
    timezone: Optional[str] = Field(
        None, description="Timezone identifier", max_length=50
    )

    # Use the same validators as ClinicBase for applicable fields
    _validate_postal_code = field_validator("postal_code")(
        ClinicBase.validate_postal_code
    )
    _validate_country = field_validator("country")(ClinicBase.validate_country)
    _validate_timezone = field_validator("timezone")(ClinicBase.validate_timezone)

    @model_validator(mode="after")
    def validate_coordinates_consistency(self):
        """Validate that both latitude and longitude are provided together."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both latitude and longitude must be provided together")
        return self
