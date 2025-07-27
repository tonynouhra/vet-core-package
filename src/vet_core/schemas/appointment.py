"""
Appointment Pydantic schemas for API validation and serialization.

This module contains Pydantic schemas for Appointment model validation,
including create, update, and response schemas with datetime validation and timezone handling.
"""

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.appointment import AppointmentPriority, AppointmentStatus, ServiceType


class AppointmentBase(BaseModel):
    """Base Appointment schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    scheduled_at: datetime = Field(
        ..., description="Scheduled date and time for the appointment"
    )
    duration_minutes: int = Field(
        30,
        description="Expected duration of the appointment in minutes",
        gt=0,
        le=480,  # Max 8 hours
    )
    service_type: ServiceType = Field(..., description="Type of veterinary service")
    service_type_other_description: Optional[str] = Field(
        None, description="Description when service_type is 'other'", max_length=200
    )
    priority: AppointmentPriority = Field(
        AppointmentPriority.NORMAL, description="Priority level of the appointment"
    )
    reason: Optional[str] = Field(
        None, description="Reason for the appointment or chief complaint"
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the appointment"
    )
    estimated_cost: Optional[Decimal] = Field(
        None,
        description="Estimated cost of the appointment",
        ge=0,
        le=Decimal("99999.99"),
    )

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: datetime) -> datetime:
        """Validate scheduled datetime."""
        # Ensure timezone awareness
        if v.tzinfo is None:
            raise ValueError("Scheduled time must be timezone-aware")

        # Check if appointment is in the future (allow some buffer for immediate appointments)
        now = datetime.now(timezone.utc)
        if v < now:
            # Allow appointments scheduled up to 5 minutes in the past (for processing delays)
            from datetime import timedelta

            if v < now - timedelta(minutes=5):
                raise ValueError("Appointment cannot be scheduled in the past")

        # Check if appointment is not too far in the future (e.g., 2 years)
        from datetime import timedelta

        max_future = now + timedelta(days=730)  # 2 years
        if v > max_future:
            raise ValueError(
                "Appointment cannot be scheduled more than 2 years in advance"
            )

        return v

    @field_validator("service_type_other_description")
    @classmethod
    def validate_service_type_other_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate service type other description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic validation for service description
            if not re.match(r"^[a-zA-Z0-9\s\-'.,()]+$", v):
                raise ValueError("Service description contains invalid characters")

        return v

    @field_validator("reason", "notes")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate text fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Check for reasonable length
            if len(v) > 2000:
                raise ValueError("Text field is too long (maximum 2000 characters)")

        return v

    @model_validator(mode="after")
    def validate_service_type_consistency(self) -> "AppointmentBase":
        """Validate that service_type 'other' has description."""
        if (
            self.service_type == ServiceType.OTHER
            and not self.service_type_other_description
        ):
            raise ValueError(
                "Service type other description is required when service type is 'other'"
            )
        return self

    @model_validator(mode="after")
    def validate_business_hours(self) -> "AppointmentBase":
        """Validate appointment is during reasonable business hours."""
        # Basic business hours validation (can be customized per clinic)
        hour = self.scheduled_at.hour
        day_of_week = self.scheduled_at.weekday()  # 0=Monday, 6=Sunday

        # Allow emergency appointments at any time
        if self.priority in [AppointmentPriority.EMERGENCY, AppointmentPriority.URGENT]:
            return self

        # Basic business hours: 7 AM to 8 PM, Monday to Saturday
        if day_of_week == 6:  # Sunday
            if not 9 <= hour <= 17:  # 9 AM to 5 PM on Sunday
                raise ValueError(
                    "Regular appointments on Sunday must be between 9 AM and 5 PM"
                )
        else:  # Monday to Saturday
            if not 7 <= hour <= 20:  # 7 AM to 8 PM
                raise ValueError("Regular appointments must be between 7 AM and 8 PM")

        return self


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""

    pet_id: UUID = Field(..., description="UUID of the pet for this appointment")
    veterinarian_id: UUID = Field(..., description="UUID of the assigned veterinarian")
    clinic_id: UUID = Field(
        ..., description="UUID of the clinic where appointment takes place"
    )
    status: AppointmentStatus = Field(
        AppointmentStatus.SCHEDULED, description="Initial status of the appointment"
    )

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v: AppointmentStatus) -> AppointmentStatus:
        """Validate initial appointment status."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                v = AppointmentStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status. Must be one of: {[status.value for status in AppointmentStatus]}"
                )

        # Only allow certain statuses for new appointments
        allowed_initial_statuses = {
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED,
        }

        if v not in allowed_initial_statuses:
            raise ValueError(
                f"Initial status must be one of: {[s.value for s in allowed_initial_statuses]}"
            )

        return v


class AppointmentUpdate(BaseModel):
    """Schema for updating an existing appointment."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    scheduled_at: Optional[datetime] = Field(
        None, description="Scheduled date and time for the appointment"
    )
    duration_minutes: Optional[int] = Field(
        None,
        description="Expected duration of the appointment in minutes",
        gt=0,
        le=480,
    )
    service_type: Optional[ServiceType] = Field(
        None, description="Type of veterinary service"
    )
    service_type_other_description: Optional[str] = Field(
        None, description="Description when service_type is 'other'", max_length=200
    )
    status: Optional[AppointmentStatus] = Field(None, description="Appointment status")
    priority: Optional[AppointmentPriority] = Field(
        None, description="Priority level of the appointment"
    )
    reason: Optional[str] = Field(
        None, description="Reason for the appointment or chief complaint"
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the appointment"
    )
    internal_notes: Optional[str] = Field(
        None, description="Internal staff notes not visible to pet owner"
    )
    estimated_cost: Optional[Decimal] = Field(
        None,
        description="Estimated cost of the appointment",
        ge=0,
        le=Decimal("99999.99"),
    )
    actual_cost: Optional[Decimal] = Field(
        None, description="Actual cost of the appointment", ge=0, le=Decimal("99999.99")
    )
    cancellation_reason: Optional[str] = Field(
        None, description="Reason for appointment cancellation", max_length=500
    )
    follow_up_needed: Optional[bool] = Field(
        None, description="Whether a follow-up appointment is needed"
    )
    follow_up_instructions: Optional[str] = Field(
        None, description="Instructions for follow-up care"
    )
    next_appointment_recommended_days: Optional[int] = Field(
        None, description="Recommended days until next appointment", gt=0, le=365
    )
    veterinarian_id: Optional[UUID] = Field(
        None, description="UUID of the assigned veterinarian (for reassignment)"
    )

    # Use the same validators as AppointmentBase for applicable fields
    _validate_scheduled_at = field_validator("scheduled_at")(
        AppointmentBase.validate_scheduled_at
    )
    _validate_service_type_other_description = field_validator(
        "service_type_other_description"
    )(AppointmentBase.validate_service_type_other_description)
    _validate_text_fields = field_validator(
        "reason", "notes", "internal_notes", "follow_up_instructions"
    )(AppointmentBase.validate_text_fields)

    @field_validator("cancellation_reason")
    @classmethod
    def validate_cancellation_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate cancellation reason."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            if len(v) > 500:
                raise ValueError(
                    "Cancellation reason is too long (maximum 500 characters)"
                )

        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "AppointmentUpdate":
        """Ensure at least one field is provided for update."""
        field_names = list(self.model_fields.keys())
        field_values = [getattr(self, name) for name in field_names]

        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self

    @model_validator(mode="after")
    def validate_status_transitions(self) -> "AppointmentUpdate":
        """Validate status transitions (basic validation)."""
        if self.status == AppointmentStatus.CANCELLED and not self.cancellation_reason:
            raise ValueError("Cancellation reason is required when status is cancelled")

        if self.status == AppointmentStatus.COMPLETED and self.actual_cost is None:
            # This is a warning rather than an error - actual cost should be provided but isn't required
            pass

        return self


class AppointmentResponse(BaseModel):
    """Schema for appointment response data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

    id: UUID = Field(..., description="Appointment's unique identifier")
    pet_id: UUID = Field(..., description="Pet's unique identifier")
    veterinarian_id: UUID = Field(..., description="Veterinarian's unique identifier")
    clinic_id: UUID = Field(..., description="Clinic's unique identifier")
    scheduled_at: datetime = Field(..., description="Scheduled date and time")
    duration_minutes: int = Field(..., description="Expected duration in minutes")
    service_type: ServiceType = Field(..., description="Type of veterinary service")
    service_type_other_description: Optional[str] = Field(
        None, description="Service type description for 'other'"
    )
    status: AppointmentStatus = Field(..., description="Current appointment status")
    priority: AppointmentPriority = Field(..., description="Priority level")
    reason: Optional[str] = Field(None, description="Reason for the appointment")
    notes: Optional[str] = Field(None, description="Additional notes")
    internal_notes: Optional[str] = Field(None, description="Internal staff notes")
    estimated_cost: Optional[Decimal] = Field(None, description="Estimated cost")
    actual_cost: Optional[Decimal] = Field(None, description="Actual cost")
    checked_in_at: Optional[datetime] = Field(None, description="Check-in timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(
        None, description="Reason for cancellation"
    )
    follow_up_needed: Optional[bool] = Field(
        None, description="Whether follow-up is needed"
    )
    follow_up_instructions: Optional[str] = Field(
        None, description="Follow-up instructions"
    )
    next_appointment_recommended_days: Optional[int] = Field(
        None, description="Recommended days until next appointment"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AppointmentListResponse(BaseModel):
    """Schema for paginated appointment list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Appointment's unique identifier")
    pet_id: UUID = Field(..., description="Pet's unique identifier")
    veterinarian_id: UUID = Field(..., description="Veterinarian's unique identifier")
    clinic_id: UUID = Field(..., description="Clinic's unique identifier")
    scheduled_at: datetime = Field(..., description="Scheduled date and time")
    duration_minutes: int = Field(..., description="Expected duration in minutes")
    service_type: ServiceType = Field(..., description="Type of veterinary service")
    status: AppointmentStatus = Field(..., description="Current appointment status")
    priority: AppointmentPriority = Field(..., description="Priority level")
    estimated_cost: Optional[Decimal] = Field(None, description="Estimated cost")
    created_at: datetime = Field(..., description="Creation timestamp")


class AppointmentStatusUpdate(BaseModel):
    """Schema for updating appointment status."""

    model_config = ConfigDict(use_enum_values=True)

    status: AppointmentStatus = Field(..., description="New appointment status")
    notes: Optional[str] = Field(None, description="Notes about the status change")
    cancellation_reason: Optional[str] = Field(
        None, description="Reason for cancellation (if applicable)"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: AppointmentStatus) -> AppointmentStatus:
        """Validate appointment status."""
        # Handle string values from Pydantic v2
        if isinstance(v, str):
            try:
                return AppointmentStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status. Must be one of: {[status.value for status in AppointmentStatus]}"
                )

        # Handle enum values
        if not isinstance(v, AppointmentStatus):
            raise ValueError(
                f"Invalid status. Must be one of: {[status.value for status in AppointmentStatus]}"
            )
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 1000:
                raise ValueError("Notes are too long (maximum 1000 characters)")
        return v

    @field_validator("cancellation_reason")
    @classmethod
    def validate_cancellation_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate cancellation reason."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 500:
                raise ValueError(
                    "Cancellation reason is too long (maximum 500 characters)"
                )
        return v

    @model_validator(mode="after")
    def validate_cancellation_consistency(self) -> "AppointmentStatusUpdate":
        """Validate cancellation reason is provided when status is cancelled."""
        if self.status == AppointmentStatus.CANCELLED and not self.cancellation_reason:
            raise ValueError("Cancellation reason is required when status is cancelled")
        return self


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling an appointment."""

    model_config = ConfigDict(validate_assignment=True)

    new_scheduled_at: datetime = Field(..., description="New scheduled date and time")
    reason: Optional[str] = Field(
        None, description="Reason for rescheduling", max_length=500
    )

    @field_validator("new_scheduled_at")
    @classmethod
    def validate_new_scheduled_at(cls, v: datetime) -> datetime:
        """Validate new scheduled datetime."""
        # Use the same validation as AppointmentBase
        return AppointmentBase.validate_scheduled_at(v)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate reschedule reason."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 500:
                raise ValueError(
                    "Reschedule reason is too long (maximum 500 characters)"
                )
        return v


class AppointmentCompletion(BaseModel):
    """Schema for completing an appointment."""

    model_config = ConfigDict(validate_assignment=True)

    actual_cost: Optional[Decimal] = Field(
        None, description="Actual cost of the appointment", ge=0, le=Decimal("99999.99")
    )
    follow_up_needed: Optional[bool] = Field(
        None, description="Whether a follow-up appointment is needed"
    )
    follow_up_instructions: Optional[str] = Field(
        None, description="Instructions for follow-up care"
    )
    next_appointment_recommended_days: Optional[int] = Field(
        None, description="Recommended days until next appointment", gt=0, le=365
    )
    completion_notes: Optional[str] = Field(
        None, description="Notes about the completed appointment"
    )

    @field_validator("follow_up_instructions", "completion_notes")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate text fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 2000:
                raise ValueError("Text field is too long (maximum 2000 characters)")
        return v

    @model_validator(mode="after")
    def validate_follow_up_consistency(self) -> "AppointmentCompletion":
        """Validate follow-up consistency."""
        if self.follow_up_needed and not self.follow_up_instructions:
            raise ValueError(
                "Follow-up instructions are required when follow-up is needed"
            )
        return self


class AppointmentSlotAvailability(BaseModel):
    """Schema for checking appointment slot availability."""

    model_config = ConfigDict(validate_assignment=True)

    veterinarian_id: UUID = Field(
        ..., description="Veterinarian ID to check availability for"
    )
    clinic_id: UUID = Field(
        ..., description="Clinic ID where appointment would take place"
    )
    start_date: datetime = Field(..., description="Start of availability check period")
    end_date: datetime = Field(..., description="End of availability check period")
    duration_minutes: int = Field(
        30, description="Required appointment duration", gt=0, le=480
    )
    service_type: Optional[ServiceType] = Field(
        None, description="Type of service (for specialized availability)"
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, v: datetime) -> datetime:
        """Validate dates are timezone-aware and not in the past."""
        if v.tzinfo is None:
            raise ValueError("Dates must be timezone-aware")

        now = datetime.now(timezone.utc)
        if v < now:
            raise ValueError("Dates cannot be in the past")

        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "AppointmentSlotAvailability":
        """Validate date range."""
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")

        # Limit the range to prevent excessive queries
        from datetime import timedelta

        max_range = timedelta(days=90)  # 3 months
        if self.end_date - self.start_date > max_range:
            raise ValueError("Date range cannot exceed 90 days")

        return self
