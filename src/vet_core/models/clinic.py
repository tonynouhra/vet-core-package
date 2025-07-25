"""
Clinic model for the vet-core package.

This module contains the Clinic SQLAlchemy model with location data,
operating hours, and relationships to veterinarians and appointments.
"""

import enum
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class ClinicStatus(enum.Enum):
    """Enumeration of clinic statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"
    UNDER_RENOVATION = "under_renovation"


class ClinicType(enum.Enum):
    """Enumeration of clinic types."""

    GENERAL_PRACTICE = "general_practice"
    EMERGENCY = "emergency"
    SPECIALTY = "specialty"
    MOBILE = "mobile"
    HOSPITAL = "hospital"
    URGENT_CARE = "urgent_care"


class Clinic(BaseModel):
    """
    Clinic model with location data and operating hours.

    Supports comprehensive clinic information including location, contact details,
    services offered, operating hours, and staff relationships with proper
    spatial indexing for location-based queries.
    """

    __tablename__ = "clinics"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Clinic with default values."""
        # Set default values if not provided
        if "status" not in kwargs:
            kwargs["status"] = ClinicStatus.ACTIVE
        if "type" not in kwargs:
            kwargs["type"] = ClinicType.GENERAL_PRACTICE
        if "accepts_new_patients" not in kwargs:
            kwargs["accepts_new_patients"] = True
        if "accepts_emergencies" not in kwargs:
            kwargs["accepts_emergencies"] = False
        if "accepts_walk_ins" not in kwargs:
            kwargs["accepts_walk_ins"] = False
        if "country" not in kwargs:
            kwargs["country"] = "US"

        super().__init__(**kwargs)

    # Basic clinic information
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="Clinic name"
    )

    license_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Veterinary clinic license number",
    )

    type: Mapped[ClinicType] = mapped_column(
        Enum(ClinicType),
        nullable=False,
        default=ClinicType.GENERAL_PRACTICE,
        index=True,
        comment="Type of veterinary clinic",
    )

    status: Mapped[ClinicStatus] = mapped_column(
        Enum(ClinicStatus),
        nullable=False,
        default=ClinicStatus.ACTIVE,
        index=True,
        comment="Current operational status of the clinic",
    )

    # Contact information
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Primary phone number"
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Primary email address"
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Clinic website URL"
    )

    # Location information
    address_line1: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Primary address line"
    )

    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Secondary address line (suite, unit, etc.)"
    )

    city: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="City"
    )

    state: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="State or province"
    )

    postal_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="Postal or ZIP code"
    )

    country: Mapped[str] = mapped_column(
        String(100), nullable=False, default="US", index=True, comment="Country code"
    )

    # Geographic coordinates for spatial queries
    latitude: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Latitude coordinate for location-based searches"
    )

    longitude: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Longitude coordinate for location-based searches"
    )

    # Operating information
    operating_hours: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Operating hours by day of week stored as JSON"
    )

    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Timezone identifier (e.g., 'America/New_York')",
    )

    # Services and capabilities
    services_offered: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="List of services offered by the clinic"
    )

    specialties: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="List of medical specialties available"
    )

    accepts_new_patients: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the clinic is accepting new patients",
    )

    accepts_emergencies: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the clinic handles emergency cases",
    )

    accepts_walk_ins: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the clinic accepts walk-in appointments",
    )

    # Facility information
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Description of the clinic and its services"
    )

    facility_features: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of facility features (parking, wheelchair access, etc.)",
    )

    equipment_available: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="List of medical equipment available"
    )

    # Capacity and staffing
    max_daily_appointments: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Maximum number of appointments per day"
    )

    number_of_exam_rooms: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Number of examination rooms"
    )

    number_of_surgery_rooms: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Number of surgery rooms"
    )

    # Insurance and payment
    insurance_accepted: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="List of accepted insurance providers"
    )

    payment_methods: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="List of accepted payment methods"
    )

    # Emergency information
    emergency_contact_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Emergency contact phone number"
    )

    after_hours_instructions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Instructions for after-hours emergencies"
    )

    # Media and branding
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="URL to clinic logo image"
    )

    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="Array of photo URLs for the clinic"
    )

    # Database constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint("license_number", name="uq_clinics_license_number"),
        # Check constraints for data integrity
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_clinics_latitude_valid",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_clinics_longitude_valid",
        ),
        CheckConstraint(
            "max_daily_appointments IS NULL OR max_daily_appointments > 0",
            name="ck_clinics_max_appointments_positive",
        ),
        CheckConstraint(
            "number_of_exam_rooms IS NULL OR number_of_exam_rooms > 0",
            name="ck_clinics_exam_rooms_positive",
        ),
        CheckConstraint(
            "number_of_surgery_rooms IS NULL OR number_of_surgery_rooms >= 0",
            name="ck_clinics_surgery_rooms_non_negative",
        ),
        # Composite indexes for efficient clinic queries
        Index("idx_clinics_location", "city", "state", "country"),
        Index("idx_clinics_status_type", "status", "type"),
        Index("idx_clinics_name_city", "name", "city"),
        Index("idx_clinics_postal_code_country", "postal_code", "country"),
        # Indexes for service-based queries
        Index("idx_clinics_accepts_new_patients", "accepts_new_patients", "status"),
        Index("idx_clinics_accepts_emergencies", "accepts_emergencies", "status"),
        Index("idx_clinics_accepts_walk_ins", "accepts_walk_ins", "status"),
        # Partial indexes for active clinics
        Index(
            "idx_clinics_active_location",
            "city",
            "state",
            postgresql_where=(status == ClinicStatus.ACTIVE),
        ),
        Index(
            "idx_clinics_active_type",
            "type",
            postgresql_where=(status == ClinicStatus.ACTIVE),
        ),
        Index(
            "idx_clinics_active_new_patients",
            "accepts_new_patients",
            postgresql_where=(status == ClinicStatus.ACTIVE),
        ),
        # Spatial indexes for location-based queries
        Index(
            "idx_clinics_coordinates",
            "latitude",
            "longitude",
            postgresql_where="latitude IS NOT NULL AND longitude IS NOT NULL",
        ),
        # GIN indexes for JSONB fields
        Index(
            "idx_clinics_operating_hours_gin", "operating_hours", postgresql_using="gin"
        ),
        Index(
            "idx_clinics_services_offered_gin",
            "services_offered",
            postgresql_using="gin",
        ),
        Index("idx_clinics_specialties_gin", "specialties", postgresql_using="gin"),
        Index(
            "idx_clinics_facility_features_gin",
            "facility_features",
            postgresql_using="gin",
        ),
        Index(
            "idx_clinics_equipment_gin", "equipment_available", postgresql_using="gin"
        ),
        Index(
            "idx_clinics_insurance_gin", "insurance_accepted", postgresql_using="gin"
        ),
        Index(
            "idx_clinics_payment_methods_gin", "payment_methods", postgresql_using="gin"
        ),
        # Full-text search indexes
        Index(
            "idx_clinics_name_search",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "idx_clinics_description_search",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )

    # Relationships
    veterinarians = relationship("Veterinarian", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")

    def __repr__(self) -> str:
        """String representation of the Clinic model."""
        return f"<Clinic(id={self.id}, name='{self.name}', city='{self.city}', status='{self.status.value}')>"

    @property
    def is_active(self) -> bool:
        """Check if the clinic is active."""
        return self.status == ClinicStatus.ACTIVE and not self.is_deleted

    @property
    def is_open_for_business(self) -> bool:
        """Check if the clinic is open for business (active and accepting patients)."""
        return self.is_active and self.accepts_new_patients

    @property
    def full_address(self) -> str:
        """Get the full formatted address."""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([self.city, self.state, self.postal_code])
        if self.country != "US":
            address_parts.append(self.country)
        return ", ".join(address_parts)

    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the clinic."""
        return self.name

    @property
    def has_coordinates(self) -> bool:
        """Check if the clinic has geographic coordinates."""
        return self.latitude is not None and self.longitude is not None

    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        """Get the clinic's coordinates as a tuple (latitude, longitude)."""
        if (
            self.has_coordinates
            and self.latitude is not None
            and self.longitude is not None
        ):
            return (self.latitude, self.longitude)
        return None

    def set_coordinates(self, latitude: float, longitude: float) -> None:
        """
        Set the clinic's geographic coordinates.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
        """
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        self.latitude = latitude
        self.longitude = longitude

    def is_open_on_day(self, day_of_week: str) -> bool:
        """
        Check if the clinic is open on a specific day of the week.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)

        Returns:
            True if the clinic is open on that day
        """
        if not self.operating_hours:
            return False

        day_schedule = self.operating_hours.get(day_of_week.lower())
        if not day_schedule:
            return False

        return bool(day_schedule.get("is_open", False))

    def get_hours_for_day(self, day_of_week: str) -> Optional[Dict[str, Any]]:
        """
        Get the operating hours for a specific day.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)

        Returns:
            Dictionary with hours information or None if closed
        """
        if not self.operating_hours:
            return None

        return self.operating_hours.get(day_of_week.lower())

    def set_operating_hours(
        self,
        day_of_week: str,
        open_time: str,
        close_time: str,
        is_open: bool = True,
        lunch_break: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Set operating hours for a specific day.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)
            open_time: Opening time in HH:MM format
            close_time: Closing time in HH:MM format
            is_open: Whether the clinic is open on this day
            lunch_break: Optional lunch break with 'start' and 'end' times
        """
        if self.operating_hours is None:
            self.operating_hours = {}

        day_schedule = {
            "is_open": is_open,
            "open_time": open_time,
            "close_time": close_time,
        }

        if lunch_break:
            day_schedule["lunch_break"] = lunch_break

        self.operating_hours[day_of_week.lower()] = day_schedule

    def add_service(self, service: str) -> None:
        """
        Add a service to the clinic's offerings.

        Args:
            service: Service name to add
        """
        if self.services_offered is None:
            self.services_offered = []

        if service not in self.services_offered:
            self.services_offered.append(service)

    def remove_service(self, service: str) -> None:
        """
        Remove a service from the clinic's offerings.

        Args:
            service: Service name to remove
        """
        if self.services_offered and service in self.services_offered:
            self.services_offered.remove(service)

    def has_service(self, service: str) -> bool:
        """
        Check if the clinic offers a specific service.

        Args:
            service: Service name to check

        Returns:
            True if the service is offered
        """
        return self.services_offered is not None and service in self.services_offered

    def add_specialty(self, specialty: str) -> None:
        """
        Add a medical specialty to the clinic.

        Args:
            specialty: Specialty name to add
        """
        if self.specialties is None:
            self.specialties = []

        if specialty not in self.specialties:
            self.specialties.append(specialty)

    def remove_specialty(self, specialty: str) -> None:
        """
        Remove a medical specialty from the clinic.

        Args:
            specialty: Specialty name to remove
        """
        if self.specialties and specialty in self.specialties:
            self.specialties.remove(specialty)

    def has_specialty(self, specialty: str) -> bool:
        """
        Check if the clinic has a specific medical specialty.

        Args:
            specialty: Specialty name to check

        Returns:
            True if the specialty is available
        """
        return self.specialties is not None and specialty in self.specialties

    def add_facility_feature(self, feature: str) -> None:
        """
        Add a facility feature to the clinic.

        Args:
            feature: Feature name to add (e.g., 'parking', 'wheelchair_accessible')
        """
        if self.facility_features is None:
            self.facility_features = []

        if feature not in self.facility_features:
            self.facility_features.append(feature)

    def has_facility_feature(self, feature: str) -> bool:
        """
        Check if the clinic has a specific facility feature.

        Args:
            feature: Feature name to check

        Returns:
            True if the feature is available
        """
        return self.facility_features is not None and feature in self.facility_features

    def accepts_insurance(self, insurance_provider: str) -> bool:
        """
        Check if the clinic accepts a specific insurance provider.

        Args:
            insurance_provider: Insurance provider name

        Returns:
            True if the insurance is accepted
        """
        return (
            self.insurance_accepted is not None
            and insurance_provider in self.insurance_accepted
        )

    def accepts_payment_method(self, payment_method: str) -> bool:
        """
        Check if the clinic accepts a specific payment method.

        Args:
            payment_method: Payment method name

        Returns:
            True if the payment method is accepted
        """
        return (
            self.payment_methods is not None and payment_method in self.payment_methods
        )

    def update_status(
        self, new_status: ClinicStatus, reason: Optional[str] = None
    ) -> None:
        """
        Update the clinic's operational status.

        Args:
            new_status: New status to set
            reason: Optional reason for the status change
        """
        old_status = self.status
        self.status = new_status

        # Log status change in description if reason provided
        if reason:
            status_note = f"Status changed from {old_status.value} to {new_status.value}: {reason}"
            if self.description:
                self.description += f"\n\n{status_note}"
            else:
                self.description = status_note

    def temporarily_close(self, reason: Optional[str] = None) -> None:
        """
        Temporarily close the clinic.

        Args:
            reason: Reason for temporary closure
        """
        self.update_status(ClinicStatus.TEMPORARILY_CLOSED, reason)
        self.accepts_new_patients = False

    def reopen(self, reason: Optional[str] = None) -> None:
        """
        Reopen the clinic (set to active status).

        Args:
            reason: Reason for reopening
        """
        self.update_status(ClinicStatus.ACTIVE, reason)
        self.accepts_new_patients = True

    def permanently_close(self, reason: Optional[str] = None) -> None:
        """
        Permanently close the clinic.

        Args:
            reason: Reason for permanent closure
        """
        self.update_status(ClinicStatus.PERMANENTLY_CLOSED, reason)
        self.accepts_new_patients = False
        self.accepts_emergencies = False
        self.accepts_walk_ins = False

    def get_status_display(self) -> str:
        """Get a human-readable status display."""
        status_display = {
            ClinicStatus.ACTIVE: "Active",
            ClinicStatus.INACTIVE: "Inactive",
            ClinicStatus.TEMPORARILY_CLOSED: "Temporarily Closed",
            ClinicStatus.PERMANENTLY_CLOSED: "Permanently Closed",
            ClinicStatus.UNDER_RENOVATION: "Under Renovation",
        }
        return status_display.get(self.status, self.status.value.title())

    def get_type_display(self) -> str:
        """Get a human-readable type display."""
        type_display = {
            ClinicType.GENERAL_PRACTICE: "General Practice",
            ClinicType.EMERGENCY: "Emergency Clinic",
            ClinicType.SPECIALTY: "Specialty Clinic",
            ClinicType.MOBILE: "Mobile Clinic",
            ClinicType.HOSPITAL: "Veterinary Hospital",
            ClinicType.URGENT_CARE: "Urgent Care",
        }
        return type_display.get(self.type, self.type.value.title())

    def calculate_distance_to(
        self, latitude: float, longitude: float
    ) -> Optional[float]:
        """
        Calculate the distance to another location using the Haversine formula.

        Args:
            latitude: Target latitude
            longitude: Target longitude

        Returns:
            Distance in kilometers, or None if clinic coordinates are not set
        """
        if not self.has_coordinates:
            return None

        import math

        # Convert latitude and longitude from degrees to radians
        # We know coordinates exist due to has_coordinates check above
        assert self.latitude is not None and self.longitude is not None
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(latitude), math.radians(longitude)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def is_within_radius(
        self, latitude: float, longitude: float, radius_km: float
    ) -> bool:
        """
        Check if the clinic is within a specified radius of a location.

        Args:
            latitude: Target latitude
            longitude: Target longitude
            radius_km: Radius in kilometers

        Returns:
            True if within radius, False otherwise
        """
        distance = self.calculate_distance_to(latitude, longitude)
        return distance is not None and distance <= radius_km

    def get_capacity_utilization(self, current_appointments: int) -> Optional[float]:
        """
        Calculate the current capacity utilization as a percentage.

        Args:
            current_appointments: Number of current appointments

        Returns:
            Utilization percentage (0-100) or None if max capacity not set
        """
        if self.max_daily_appointments is None or self.max_daily_appointments == 0:
            return None

        return min(100.0, (current_appointments / self.max_daily_appointments) * 100)

    def is_at_capacity(self, current_appointments: int) -> bool:
        """
        Check if the clinic is at or over capacity.

        Args:
            current_appointments: Number of current appointments

        Returns:
            True if at or over capacity
        """
        if self.max_daily_appointments is None:
            return False

        return current_appointments >= self.max_daily_appointments
