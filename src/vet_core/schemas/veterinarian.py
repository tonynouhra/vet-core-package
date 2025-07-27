"""
Veterinarian Pydantic schemas for API validation and serialization.

This module contains Pydantic schemas for Veterinarian model validation,
including create, update, and response schemas with credential validation.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.veterinarian import EmploymentType, LicenseStatus, VeterinarianStatus


class CertificationSchema(BaseModel):
    """Schema for professional certifications."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Name of the certification")
    issuing_organization: str = Field(
        ..., description="Organization that issued the certification"
    )
    date_obtained: date = Field(..., description="Date when certification was obtained")
    expiry_date: Optional[date] = Field(
        None, description="Expiry date of the certification"
    )
    certification_number: Optional[str] = Field(
        None, description="Certification number or ID"
    )

    @field_validator("name", "issuing_organization")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required string fields."""
        if not v or not v.strip():
            raise ValueError("Field is required")
        return v.strip()

    @field_validator("date_obtained")
    @classmethod
    def validate_date_obtained(cls, v: date) -> date:
        """Validate date obtained is not in the future."""
        if v > date.today():
            raise ValueError("Date obtained cannot be in the future")
        return v

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate expiry date is after obtained date."""
        # Note: We can't validate against date_obtained here since it's not available
        # This validation would be done at the model level
        return v

    @field_validator("certification_number")
    @classmethod
    def validate_certification_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate certification number format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic alphanumeric validation
            if not re.match(r"^[A-Z0-9\-]+$", v.upper()):
                raise ValueError(
                    "Certification number can only contain letters, numbers, and hyphens"
                )

        return v.upper() if v else None

    @model_validator(mode="after")
    def validate_expiry_after_obtained(self) -> "CertificationSchema":
        """Validate expiry date is after obtained date."""
        if self.expiry_date and self.expiry_date <= self.date_obtained:
            raise ValueError("Expiry date must be after the date obtained")
        return self


class ProfessionalMembershipSchema(BaseModel):
    """Schema for professional memberships."""

    model_config = ConfigDict(from_attributes=True)

    organization_name: str = Field(
        ..., description="Name of the professional organization"
    )
    membership_type: Optional[str] = Field(None, description="Type of membership")
    member_since: Optional[date] = Field(
        None, description="Date when membership started"
    )
    membership_number: Optional[str] = Field(
        None, description="Membership number or ID"
    )
    is_active: bool = Field(
        True, description="Whether the membership is currently active"
    )

    @field_validator("organization_name")
    @classmethod
    def validate_organization_name(cls, v: str) -> str:
        """Validate organization name."""
        if not v or not v.strip():
            raise ValueError("Organization name is required")
        return v.strip()

    @field_validator("member_since")
    @classmethod
    def validate_member_since(cls, v: Optional[date]) -> Optional[date]:
        """Validate member since date is not in the future."""
        if v and v > date.today():
            raise ValueError("Member since date cannot be in the future")
        return v


class AvailabilitySlotSchema(BaseModel):
    """Schema for availability time slots."""

    model_config = ConfigDict(from_attributes=True)

    start_time: str = Field(..., description="Start time in HH:MM format")
    end_time: str = Field(..., description="End time in HH:MM format")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format."""
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")
        return v

    @model_validator(mode="after")
    def validate_time_order(self) -> "AvailabilitySlotSchema":
        """Validate end time is after start time."""

        def time_to_minutes(time_str: str) -> int:
            hours, minutes = map(int, time_str.split(":"))
            return hours * 60 + minutes

        start_minutes = time_to_minutes(self.start_time)
        end_minutes = time_to_minutes(self.end_time)

        if end_minutes <= start_minutes:
            raise ValueError("End time must be after start time")

        return self


class DayAvailabilitySchema(BaseModel):
    """Schema for daily availability."""

    model_config = ConfigDict(from_attributes=True)

    is_available: bool = Field(..., description="Whether available on this day")
    start_time: Optional[str] = Field(None, description="Start time in HH:MM format")
    end_time: Optional[str] = Field(None, description="End time in HH:MM format")
    breaks: Optional[List[AvailabilitySlotSchema]] = Field(
        None, description="Break periods during the day"
    )

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format."""
        if v is None:
            return v

        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")
        return v

    @model_validator(mode="after")
    def validate_availability_consistency(self) -> "DayAvailabilitySchema":
        """Validate availability consistency."""
        if self.is_available:
            if not self.start_time or not self.end_time:
                raise ValueError("Start and end times are required when available")

            # Validate time order
            def time_to_minutes(time_str: str) -> int:
                hours, minutes = map(int, time_str.split(":"))
                return hours * 60 + minutes

            start_minutes = time_to_minutes(self.start_time)
            end_minutes = time_to_minutes(self.end_time)

            if end_minutes <= start_minutes:
                raise ValueError("End time must be after start time")

            # Validate breaks are within working hours
            if self.breaks:
                for break_slot in self.breaks:
                    break_start = time_to_minutes(break_slot.start_time)
                    break_end = time_to_minutes(break_slot.end_time)

                    if break_start < start_minutes or break_end > end_minutes:
                        raise ValueError("Break times must be within working hours")

        return self


class VeterinarianBase(BaseModel):
    """Base Veterinarian schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    license_number: str = Field(
        ..., description="Veterinary license number", max_length=100
    )
    license_state: str = Field(
        ..., description="State or province where license was issued", max_length=100
    )
    license_country: str = Field(
        "US", description="Country where license was issued", max_length=100
    )
    license_issued_date: Optional[date] = Field(
        None, description="Date when license was first issued"
    )
    license_expiry_date: Optional[date] = Field(
        None, description="Date when license expires"
    )
    veterinary_school: Optional[str] = Field(
        None, description="Name of veterinary school attended", max_length=200
    )
    graduation_year: Optional[int] = Field(
        None, description="Year of graduation from veterinary school", ge=1800, le=2030
    )
    degree_type: Optional[str] = Field(
        "DVM", description="Type of veterinary degree (DVM, VMD, etc.)", max_length=50
    )
    years_of_experience: int = Field(
        0, description="Years of veterinary experience", ge=0, le=70
    )
    employment_type: EmploymentType = Field(
        EmploymentType.FULL_TIME, description="Type of employment arrangement"
    )
    specializations: Optional[List[str]] = Field(
        None, description="List of medical specializations and areas of expertise"
    )
    services_provided: Optional[List[str]] = Field(
        None, description="List of services this veterinarian provides"
    )
    species_expertise: Optional[List[str]] = Field(
        None, description="List of animal species this veterinarian specializes in"
    )
    is_accepting_new_patients: bool = Field(
        True, description="Whether veterinarian is accepting new patients"
    )
    appointment_duration_minutes: Optional[int] = Field(
        30, description="Default appointment duration in minutes", gt=0, le=480
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum number of appointments per day", gt=0
    )
    bio: Optional[str] = Field(
        None, description="Professional biography and background"
    )
    professional_interests: Optional[str] = Field(
        None, description="Professional interests and research areas"
    )
    languages_spoken: Optional[List[str]] = Field(
        None, description="Languages spoken by the veterinarian"
    )
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact phone number", max_length=20
    )

    @field_validator("license_number")
    @classmethod
    def validate_license_number(cls, v: str) -> str:
        """Validate license number format."""
        if not v or not v.strip():
            raise ValueError("License number is required")

        # Basic alphanumeric validation with hyphens
        if not re.match(r"^[A-Z0-9\-]+$", v.upper()):
            raise ValueError(
                "License number can only contain letters, numbers, and hyphens"
            )

        return v.upper().strip()

    @field_validator("license_state", "license_country")
    @classmethod
    def validate_location_fields(cls, v: str) -> str:
        """Validate location fields."""
        if not v or not v.strip():
            raise ValueError("Field is required")

        # Basic validation for state/country codes
        if not re.match(r"^[A-Z\s\-]+$", v.upper()):
            raise ValueError("Field can only contain letters, spaces, and hyphens")

        return v.upper().strip()

    @field_validator("license_issued_date", "license_expiry_date")
    @classmethod
    def validate_license_dates(cls, v: Optional[date]) -> Optional[date]:
        """Validate license dates."""
        if v is not None:
            # License issued date should not be in the future
            if v > date.today():
                raise ValueError("License date cannot be in the future")
        return v

    @field_validator("veterinary_school")
    @classmethod
    def validate_veterinary_school(cls, v: Optional[str]) -> Optional[str]:
        """Validate veterinary school name."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Allow letters, numbers, spaces, and common punctuation
            if not re.match(r"^[a-zA-Z0-9\s\-'.,()&]+$", v):
                raise ValueError("School name contains invalid characters")

        return v

    @field_validator("degree_type")
    @classmethod
    def validate_degree_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate degree type."""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return "DVM"

            # Common veterinary degree types
            valid_degrees = {
                "DVM",
                "VMD",
                "BVS",
                "BVMS",
                "BVM&S",
                "VET.MED.",
                "DR.MED.VET.",
            }
            if v not in valid_degrees:
                # Allow other formats but validate basic structure
                if not re.match(r"^[A-Z.&\s]+$", v):
                    raise ValueError("Degree type contains invalid characters")

        return v

    @field_validator("graduation_year")
    @classmethod
    def validate_graduation_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate graduation year."""
        if v is not None:
            current_year = date.today().year
            if v > current_year + 5:  # Allow some future dates for students
                raise ValueError("Graduation year cannot be too far in the future")
        return v

    @field_validator(
        "specializations", "services_provided", "species_expertise", "languages_spoken"
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

    @field_validator("emergency_contact_number")
    @classmethod
    def validate_emergency_contact_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate emergency contact phone number."""
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

    @field_validator("bio", "professional_interests")
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
    def validate_license_dates_consistency(self) -> "VeterinarianBase":
        """Validate license date consistency."""
        if self.license_issued_date and self.license_expiry_date:
            if self.license_expiry_date <= self.license_issued_date:
                raise ValueError("License expiry date must be after issued date")
        return self

    @model_validator(mode="after")
    def validate_experience_consistency(self) -> "VeterinarianBase":
        """Validate years of experience consistency with graduation year."""
        if self.graduation_year and self.years_of_experience:
            current_year = date.today().year
            max_possible_experience = current_year - self.graduation_year

            if (
                self.years_of_experience > max_possible_experience + 2
            ):  # Allow some flexibility
                raise ValueError(
                    "Years of experience seems inconsistent with graduation year"
                )

        return self


class VeterinarianCreate(VeterinarianBase):
    """Schema for creating a new veterinarian."""

    user_id: UUID = Field(..., description="UUID of the associated user account")
    clinic_id: UUID = Field(
        ..., description="UUID of the primary clinic where veterinarian works"
    )
    status: VeterinarianStatus = Field(
        VeterinarianStatus.ACTIVE, description="Initial veterinarian status"
    )
    license_status: LicenseStatus = Field(
        LicenseStatus.ACTIVE, description="Initial license status"
    )
    hire_date: Optional[date] = Field(None, description="Date hired at current clinic")
    additional_certifications: Optional[List[CertificationSchema]] = Field(
        None, description="Additional certifications and credentials"
    )
    professional_memberships: Optional[List[ProfessionalMembershipSchema]] = Field(
        None, description="Professional organizations and memberships"
    )
    availability: Optional[Dict[str, DayAvailabilitySchema]] = Field(
        None, description="Weekly availability schedule"
    )

    @field_validator("hire_date")
    @classmethod
    def validate_hire_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate hire date is not in the future."""
        if v and v > date.today():
            raise ValueError("Hire date cannot be in the future")
        return v

    @field_validator("additional_certifications")
    @classmethod
    def validate_additional_certifications(
        cls, v: Optional[List[CertificationSchema]]
    ) -> Optional[List[CertificationSchema]]:
        """Validate additional certifications."""
        if v is not None and len(v) > 20:  # Reasonable limit
            raise ValueError("Maximum 20 additional certifications allowed")
        return v

    @field_validator("professional_memberships")
    @classmethod
    def validate_professional_memberships(
        cls, v: Optional[List[ProfessionalMembershipSchema]]
    ) -> Optional[List[ProfessionalMembershipSchema]]:
        """Validate professional memberships."""
        if v is not None and len(v) > 15:  # Reasonable limit
            raise ValueError("Maximum 15 professional memberships allowed")
        return v

    @field_validator("availability")
    @classmethod
    def validate_availability(
        cls, v: Optional[Dict[str, DayAvailabilitySchema]]
    ) -> Optional[Dict[str, DayAvailabilitySchema]]:
        """Validate availability schedule."""
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

        for day, schedule in v.items():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day of week: {day}")

            if not isinstance(schedule, DayAvailabilitySchema):
                raise ValueError(
                    f"Availability for {day} must be a DayAvailabilitySchema"
                )

        return v


class VeterinarianUpdate(BaseModel):
    """Schema for updating an existing veterinarian."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    license_number: Optional[str] = Field(
        None, description="Veterinary license number", max_length=100
    )
    license_state: Optional[str] = Field(
        None, description="State or province where license was issued", max_length=100
    )
    license_country: Optional[str] = Field(
        None, description="Country where license was issued", max_length=100
    )
    license_status: Optional[LicenseStatus] = Field(None, description="License status")
    license_issued_date: Optional[date] = Field(
        None, description="Date when license was first issued"
    )
    license_expiry_date: Optional[date] = Field(
        None, description="Date when license expires"
    )
    veterinary_school: Optional[str] = Field(
        None, description="Name of veterinary school attended", max_length=200
    )
    graduation_year: Optional[int] = Field(
        None, description="Year of graduation from veterinary school", ge=1800, le=2030
    )
    degree_type: Optional[str] = Field(
        None, description="Type of veterinary degree (DVM, VMD, etc.)", max_length=50
    )
    status: Optional[VeterinarianStatus] = Field(
        None, description="Veterinarian status"
    )
    employment_type: Optional[EmploymentType] = Field(
        None, description="Type of employment arrangement"
    )
    years_of_experience: Optional[int] = Field(
        None, description="Years of veterinary experience", ge=0, le=70
    )
    hire_date: Optional[date] = Field(None, description="Date hired at current clinic")
    specializations: Optional[List[str]] = Field(
        None, description="List of medical specializations and areas of expertise"
    )
    services_provided: Optional[List[str]] = Field(
        None, description="List of services this veterinarian provides"
    )
    species_expertise: Optional[List[str]] = Field(
        None, description="List of animal species this veterinarian specializes in"
    )
    is_accepting_new_patients: Optional[bool] = Field(
        None, description="Whether veterinarian is accepting new patients"
    )
    appointment_duration_minutes: Optional[int] = Field(
        None, description="Default appointment duration in minutes", gt=0, le=480
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum number of appointments per day", gt=0
    )
    bio: Optional[str] = Field(
        None, description="Professional biography and background"
    )
    professional_interests: Optional[str] = Field(
        None, description="Professional interests and research areas"
    )
    languages_spoken: Optional[List[str]] = Field(
        None, description="Languages spoken by the veterinarian"
    )
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact phone number", max_length=20
    )
    additional_certifications: Optional[List[CertificationSchema]] = Field(
        None, description="Additional certifications and credentials"
    )
    professional_memberships: Optional[List[ProfessionalMembershipSchema]] = Field(
        None, description="Professional organizations and memberships"
    )
    availability: Optional[Dict[str, DayAvailabilitySchema]] = Field(
        None, description="Weekly availability schedule"
    )
    clinic_id: Optional[UUID] = Field(
        None, description="UUID of the primary clinic (for transfers)"
    )

    # Use the same validators as VeterinarianBase for applicable fields
    _validate_license_number = field_validator("license_number")(
        VeterinarianBase.validate_license_number
    )
    _validate_location_fields = field_validator("license_state", "license_country")(
        VeterinarianBase.validate_location_fields
    )
    _validate_license_dates = field_validator(
        "license_issued_date", "license_expiry_date"
    )(VeterinarianBase.validate_license_dates)
    _validate_veterinary_school = field_validator("veterinary_school")(
        VeterinarianBase.validate_veterinary_school
    )
    _validate_degree_type = field_validator("degree_type")(
        VeterinarianBase.validate_degree_type
    )
    _validate_graduation_year = field_validator("graduation_year")(
        VeterinarianBase.validate_graduation_year
    )
    _validate_string_lists = field_validator(
        "specializations", "services_provided", "species_expertise", "languages_spoken"
    )(VeterinarianBase.validate_string_lists)
    _validate_emergency_contact_number = field_validator("emergency_contact_number")(
        VeterinarianBase.validate_emergency_contact_number
    )
    _validate_text_fields = field_validator("bio", "professional_interests")(
        VeterinarianBase.validate_text_fields
    )
    _validate_hire_date = field_validator("hire_date")(
        VeterinarianCreate.validate_hire_date
    )
    _validate_additional_certifications = field_validator("additional_certifications")(
        VeterinarianCreate.validate_additional_certifications
    )
    _validate_professional_memberships = field_validator("professional_memberships")(
        VeterinarianCreate.validate_professional_memberships
    )
    _validate_availability = field_validator("availability")(
        VeterinarianCreate.validate_availability
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "VeterinarianUpdate":
        """Ensure at least one field is provided for update."""
        field_names = list(self.model_fields.keys())
        field_values = [getattr(self, name) for name in field_names]

        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self


class VeterinarianResponse(BaseModel):
    """Schema for veterinarian response data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

    id: UUID = Field(..., description="Veterinarian's unique identifier")
    user_id: UUID = Field(..., description="Associated user account ID")
    clinic_id: UUID = Field(..., description="Primary clinic ID")
    license_number: str = Field(..., description="Veterinary license number")
    license_state: str = Field(..., description="License state or province")
    license_country: str = Field(..., description="License country")
    license_status: LicenseStatus = Field(..., description="Current license status")
    license_issued_date: Optional[date] = Field(None, description="License issued date")
    license_expiry_date: Optional[date] = Field(None, description="License expiry date")
    veterinary_school: Optional[str] = Field(
        None, description="Veterinary school attended"
    )
    graduation_year: Optional[int] = Field(None, description="Graduation year")
    degree_type: Optional[str] = Field(None, description="Veterinary degree type")
    status: VeterinarianStatus = Field(..., description="Current status")
    employment_type: EmploymentType = Field(..., description="Employment type")
    years_of_experience: int = Field(..., description="Years of experience")
    hire_date: Optional[date] = Field(None, description="Hire date at current clinic")
    specializations: Optional[List[str]] = Field(
        None, description="Medical specializations"
    )
    services_provided: Optional[List[str]] = Field(
        None, description="Services provided"
    )
    species_expertise: Optional[List[str]] = Field(
        None, description="Species expertise"
    )
    is_accepting_new_patients: bool = Field(..., description="Accepting new patients")
    appointment_duration_minutes: Optional[int] = Field(
        None, description="Default appointment duration"
    )
    max_daily_appointments: Optional[int] = Field(
        None, description="Maximum daily appointments"
    )
    rating: Decimal = Field(..., description="Average rating from reviews")
    total_reviews: int = Field(..., description="Total number of reviews")
    bio: Optional[str] = Field(None, description="Professional biography")
    professional_interests: Optional[str] = Field(
        None, description="Professional interests"
    )
    languages_spoken: Optional[List[str]] = Field(None, description="Languages spoken")
    emergency_contact_number: Optional[str] = Field(
        None, description="Emergency contact number"
    )
    additional_certifications: Optional[List[Dict[str, Any]]] = Field(
        None, description="Additional certifications"
    )
    professional_memberships: Optional[List[Dict[str, Any]]] = Field(
        None, description="Professional memberships"
    )
    availability: Optional[Dict[str, Any]] = Field(
        None, description="Weekly availability schedule"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class VeterinarianListResponse(BaseModel):
    """Schema for paginated veterinarian list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Veterinarian's unique identifier")
    user_id: UUID = Field(..., description="Associated user account ID")
    clinic_id: UUID = Field(..., description="Primary clinic ID")
    license_number: str = Field(..., description="Veterinary license number")
    status: VeterinarianStatus = Field(..., description="Current status")
    employment_type: EmploymentType = Field(..., description="Employment type")
    years_of_experience: int = Field(..., description="Years of experience")
    specializations: Optional[List[str]] = Field(
        None, description="Medical specializations"
    )
    is_accepting_new_patients: bool = Field(..., description="Accepting new patients")
    rating: Decimal = Field(..., description="Average rating from reviews")
    total_reviews: int = Field(..., description="Total number of reviews")
    created_at: datetime = Field(..., description="Creation timestamp")


class VeterinarianStatusUpdate(BaseModel):
    """Schema for updating veterinarian status."""

    model_config = ConfigDict(use_enum_values=True)

    status: VeterinarianStatus = Field(..., description="New veterinarian status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: VeterinarianStatus) -> VeterinarianStatus:
        """Validate veterinarian status."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                return VeterinarianStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status. Must be one of: {[status.value for status in VeterinarianStatus]}"
                )

        # Handle enum values
        if not isinstance(v, VeterinarianStatus):
            raise ValueError(
                f"Invalid status. Must be one of: {[status.value for status in VeterinarianStatus]}"
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


class VeterinarianLicenseUpdate(BaseModel):
    """Schema for updating veterinarian license information."""

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    license_number: Optional[str] = Field(None, description="New license number")
    license_state: Optional[str] = Field(None, description="New license state")
    license_country: Optional[str] = Field(None, description="New license country")
    license_status: Optional[LicenseStatus] = Field(
        None, description="New license status"
    )
    license_issued_date: Optional[date] = Field(
        None, description="New license issued date"
    )
    license_expiry_date: Optional[date] = Field(
        None, description="New license expiry date"
    )

    # Use the same validators as VeterinarianBase
    _validate_license_number = field_validator("license_number")(
        VeterinarianBase.validate_license_number
    )
    _validate_location_fields = field_validator("license_state", "license_country")(
        VeterinarianBase.validate_location_fields
    )
    _validate_license_dates = field_validator(
        "license_issued_date", "license_expiry_date"
    )(VeterinarianBase.validate_license_dates)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "VeterinarianLicenseUpdate":
        """Ensure at least one field is provided for update."""
        field_names = list(self.model_fields.keys())
        field_values = [getattr(self, name) for name in field_names]

        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self


class VeterinarianAvailabilityUpdate(BaseModel):
    """Schema for updating veterinarian availability."""

    model_config = ConfigDict(validate_assignment=True)

    availability: Dict[str, DayAvailabilitySchema] = Field(
        ..., description="Weekly availability schedule"
    )

    @field_validator("availability")
    @classmethod
    def validate_availability(
        cls, v: Dict[str, DayAvailabilitySchema]
    ) -> Dict[str, DayAvailabilitySchema]:
        """Validate availability schedule."""
        valid_days = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }

        for day, schedule in v.items():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day of week: {day}")

            if not isinstance(schedule, DayAvailabilitySchema):
                raise ValueError(
                    f"Availability for {day} must be a DayAvailabilitySchema"
                )

        return v


class VeterinarianSearchFilters(BaseModel):
    """Schema for veterinarian search filters."""

    model_config = ConfigDict(validate_assignment=True)

    clinic_id: Optional[UUID] = Field(None, description="Filter by clinic")
    specializations: Optional[List[str]] = Field(
        None, description="Filter by specializations"
    )
    services_provided: Optional[List[str]] = Field(
        None, description="Filter by services"
    )
    species_expertise: Optional[List[str]] = Field(
        None, description="Filter by species expertise"
    )
    is_accepting_new_patients: Optional[bool] = Field(
        None, description="Filter by patient acceptance"
    )
    min_rating: Optional[float] = Field(
        None, description="Minimum rating filter", ge=0, le=5
    )
    min_experience_years: Optional[int] = Field(
        None, description="Minimum years of experience", ge=0
    )
    employment_type: Optional[EmploymentType] = Field(
        None, description="Filter by employment type"
    )
    languages_spoken: Optional[List[str]] = Field(
        None, description="Filter by languages spoken"
    )

    @field_validator(
        "specializations", "services_provided", "species_expertise", "languages_spoken"
    )
    @classmethod
    def validate_filter_lists(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate filter lists."""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("Filter must be a list of strings")

        # Remove empty strings and duplicates
        filtered = list(set(item.strip() for item in v if item and item.strip()))
        return filtered if filtered else None


class VeterinarianRatingUpdate(BaseModel):
    """Schema for updating veterinarian rating."""

    model_config = ConfigDict(validate_assignment=True)

    new_rating: Decimal = Field(
        ..., description="New rating to add (0.0 to 5.0)", ge=0, le=5
    )
    review_comment: Optional[str] = Field(
        None, description="Optional review comment", max_length=1000
    )

    @field_validator("review_comment")
    @classmethod
    def validate_review_comment(cls, v: Optional[str]) -> Optional[str]:
        """Validate review comment."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 1000:
                raise ValueError("Review comment is too long (maximum 1000 characters)")
        return v
