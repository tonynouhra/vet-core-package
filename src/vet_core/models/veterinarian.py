"""
Veterinarian model for the vet-core package.

This module contains the Veterinarian SQLAlchemy model with credentials,
specializations, and relationships to users, clinics, and appointments.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vet_core.database.types import JSONType

from .base import BaseModel


class VeterinarianStatus(enum.Enum):
    """Enumeration of veterinarian statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class LicenseStatus(enum.Enum):
    """Enumeration of veterinary license statuses."""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING_RENEWAL = "pending_renewal"


class EmploymentType(enum.Enum):
    """Enumeration of employment types."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    LOCUM = "locum"
    OWNER = "owner"
    PARTNER = "partner"


class Veterinarian(BaseModel):
    """
    Veterinarian model with credentials and specializations.

    Supports professional credentials, specializations, clinic associations,
    availability schedules, and rating/review aggregation with proper
    relationships to users and clinics.
    """

    __tablename__ = "veterinarians"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Veterinarian with default values."""
        # Set default values if not provided
        if "status" not in kwargs:
            kwargs["status"] = VeterinarianStatus.ACTIVE
        if "license_status" not in kwargs:
            kwargs["license_status"] = LicenseStatus.ACTIVE
        if "employment_type" not in kwargs:
            kwargs["employment_type"] = EmploymentType.FULL_TIME
        if "is_accepting_new_patients" not in kwargs:
            kwargs["is_accepting_new_patients"] = True
        if "years_of_experience" not in kwargs:
            kwargs["years_of_experience"] = 0
        if "rating" not in kwargs:
            kwargs["rating"] = Decimal("0.0")
        if "total_reviews" not in kwargs:
            kwargs["total_reviews"] = 0

        super().__init__(**kwargs)

    # Relationship to User model
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="UUID of the associated user account",
    )

    # Primary clinic association
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the primary clinic where veterinarian works",
    )

    # Professional credentials
    license_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Veterinary license number",
    )

    license_state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="State or province where license was issued",
    )

    license_country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="US",
        comment="Country where license was issued",
    )

    license_status: Mapped[LicenseStatus] = mapped_column(
        Enum(LicenseStatus),
        nullable=False,
        default=LicenseStatus.ACTIVE,
        index=True,
        comment="Current status of the veterinary license",
    )

    license_issued_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Date when license was first issued"
    )

    license_expiry_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, index=True, comment="Date when license expires"
    )

    # Education and qualifications
    veterinary_school: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="Name of veterinary school attended"
    )

    graduation_year: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Year of graduation from veterinary school"
    )

    degree_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Type of veterinary degree (DVM, VMD, etc.)"
    )

    additional_certifications: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="Additional certifications and credentials stored as JSON array",
    )

    # Professional information
    status: Mapped[VeterinarianStatus] = mapped_column(
        Enum(VeterinarianStatus),
        nullable=False,
        default=VeterinarianStatus.ACTIVE,
        index=True,
        comment="Current employment status",
    )

    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType),
        nullable=False,
        default=EmploymentType.FULL_TIME,
        index=True,
        comment="Type of employment arrangement",
    )

    years_of_experience: Mapped[int] = mapped_column(
        nullable=False, default=0, comment="Years of veterinary experience"
    )

    hire_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Date hired at current clinic"
    )

    # Specializations and expertise
    specializations: Mapped[Optional[List[str]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="List of medical specializations and areas of expertise",
    )

    services_provided: Mapped[Optional[List[str]]] = mapped_column(
        JSONType, nullable=True, comment="List of services this veterinarian provides"
    )

    species_expertise: Mapped[Optional[List[str]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="List of animal species this veterinarian specializes in",
    )

    # Availability and scheduling
    availability: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True, comment="Weekly availability schedule stored as JSON"
    )

    is_accepting_new_patients: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether veterinarian is accepting new patients",
    )

    appointment_duration_minutes: Mapped[Optional[int]] = mapped_column(
        nullable=True, default=30, comment="Default appointment duration in minutes"
    )

    max_daily_appointments: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Maximum number of appointments per day"
    )

    # Rating and reviews
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),  # 0.00 to 5.00
        nullable=False,
        default=Decimal("0.0"),
        index=True,
        comment="Average rating from patient reviews (0.00 to 5.00)",
    )

    total_reviews: Mapped[int] = mapped_column(
        nullable=False, default=0, comment="Total number of reviews received"
    )

    # Professional profile
    bio: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Professional biography and background"
    )

    professional_interests: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Professional interests and research areas"
    )

    languages_spoken: Mapped[Optional[List[str]]] = mapped_column(
        JSONType, nullable=True, comment="Languages spoken by the veterinarian"
    )

    # Contact and emergency information
    emergency_contact_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Emergency contact phone number"
    )

    # Professional memberships and affiliations
    professional_memberships: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONType, nullable=True, comment="Professional organizations and memberships"
    )

    # Database constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint("user_id", name="uq_veterinarians_user_id"),
        UniqueConstraint("license_number", name="uq_veterinarians_license_number"),
        # Check constraints for data integrity
        CheckConstraint(
            "years_of_experience >= 0", name="ck_veterinarians_experience_non_negative"
        ),
        CheckConstraint(
            "graduation_year IS NULL OR graduation_year > 1800",
            name="ck_veterinarians_graduation_year_valid",
        ),
        CheckConstraint(
            "rating >= 0 AND rating <= 5", name="ck_veterinarians_rating_valid"
        ),
        CheckConstraint(
            "total_reviews >= 0", name="ck_veterinarians_reviews_non_negative"
        ),
        CheckConstraint(
            "appointment_duration_minutes IS NULL OR appointment_duration_minutes > 0",
            name="ck_veterinarians_appointment_duration_positive",
        ),
        CheckConstraint(
            "max_daily_appointments IS NULL OR max_daily_appointments > 0",
            name="ck_veterinarians_max_appointments_positive",
        ),
        CheckConstraint(
            "license_issued_date IS NULL OR license_issued_date <= CURRENT_DATE",
            name="ck_veterinarians_license_issued_not_future",
        ),
        CheckConstraint(
            "license_expiry_date IS NULL OR license_expiry_date > license_issued_date",
            name="ck_veterinarians_license_expiry_after_issued",
        ),
        CheckConstraint(
            "hire_date IS NULL OR hire_date <= CURRENT_DATE",
            name="ck_veterinarians_hire_date_not_future",
        ),
        # Composite indexes for efficient veterinarian queries
        Index("idx_veterinarians_clinic_status", "clinic_id", "status"),
        Index("idx_veterinarians_license_status", "license_number", "license_status"),
        Index(
            "idx_veterinarians_status_accepting", "status", "is_accepting_new_patients"
        ),
        Index("idx_veterinarians_rating_reviews", "rating", "total_reviews"),
        Index("idx_veterinarians_experience_rating", "years_of_experience", "rating"),
        # Indexes for license management
        Index(
            "idx_veterinarians_license_expiry", "license_expiry_date", "license_status"
        ),
        Index("idx_veterinarians_license_state", "license_state", "license_country"),
        # Partial indexes for active veterinarians
        Index(
            "idx_veterinarians_active_clinic",
            "clinic_id",
            postgresql_where=(status == VeterinarianStatus.ACTIVE),
        ),
        Index(
            "idx_veterinarians_active_accepting",
            "is_accepting_new_patients",
            postgresql_where=(status == VeterinarianStatus.ACTIVE),
        ),
        Index(
            "idx_veterinarians_active_rating",
            "rating",
            postgresql_where=(status == VeterinarianStatus.ACTIVE),
        ),
        # Indexes for license expiry monitoring
        Index(
            "idx_veterinarians_expiring_licenses",
            "license_expiry_date",
            postgresql_where=(license_status == LicenseStatus.ACTIVE),
        ),
        # GIN indexes for JSONB fields
        Index(
            "idx_veterinarians_specializations_gin",
            "specializations",
            postgresql_using="gin",
        ),
        Index(
            "idx_veterinarians_services_gin",
            "services_provided",
            postgresql_using="gin",
        ),
        Index(
            "idx_veterinarians_species_gin", "species_expertise", postgresql_using="gin"
        ),
        Index(
            "idx_veterinarians_availability_gin", "availability", postgresql_using="gin"
        ),
        Index(
            "idx_veterinarians_certifications_gin",
            "additional_certifications",
            postgresql_using="gin",
        ),
        Index(
            "idx_veterinarians_memberships_gin",
            "professional_memberships",
            postgresql_using="gin",
        ),
        Index(
            "idx_veterinarians_languages_gin",
            "languages_spoken",
            postgresql_using="gin",
        ),
        # Full-text search indexes
        Index(
            "idx_veterinarians_bio_search",
            "bio",
            postgresql_using="gin",
            postgresql_ops={"bio": "gin_trgm_ops"},
        ),
        Index(
            "idx_veterinarians_school_search",
            "veterinary_school",
            postgresql_using="gin",
            postgresql_ops={"veterinary_school": "gin_trgm_ops"},
        ),
    )

    # Relationships
    user = relationship("User", back_populates="veterinarian")
    clinic = relationship("Clinic", back_populates="veterinarians")
    appointments = relationship("Appointment", back_populates="veterinarian")

    def __repr__(self) -> str:
        """Return string representation of the Veterinarian model."""
        return (
            f"<Veterinarian(id={self.id}, user_id={self.user_id}, "
            f"license_number='{self.license_number}', status='{self.status.value}')>"
        )

    @property
    def is_active(self) -> bool:
        """Check if the veterinarian is active."""
        return (
            self.status == VeterinarianStatus.ACTIVE
            and self.license_status == LicenseStatus.ACTIVE
            and not self.is_deleted
        )

    @property
    def is_available_for_appointments(self) -> bool:
        """Check if the veterinarian is available for new appointments."""
        return self.is_active and self.is_accepting_new_patients

    @property
    def license_is_valid(self) -> bool:
        """Check if the veterinary license is currently valid."""
        if self.license_status != LicenseStatus.ACTIVE:
            return False

        if self.license_expiry_date:
            return self.license_expiry_date >= date.today()

        return True

    @property
    def license_expires_soon(self) -> bool:
        """Check if the license expires within 30 days."""
        if not self.license_expiry_date:
            return False

        from datetime import timedelta

        warning_date = date.today() + timedelta(days=30)
        return self.license_expiry_date <= warning_date

    @property
    def display_name(self) -> str:
        """Get a display-friendly name (will need User relationship)."""
        # This would typically use the related User model
        return f"Dr. {self.license_number}"  # Placeholder until User relationship is available

    @property
    def full_credentials(self) -> str:
        """Get full credentials display."""
        credentials = []
        if self.degree_type:
            credentials.append(self.degree_type)

        if self.specializations:
            credentials.extend(self.specializations)

        return ", ".join(credentials) if credentials else "DVM"

    @property
    def rating_display(self) -> str:
        """Get a formatted rating display."""
        if self.total_reviews == 0:
            return "No reviews yet"

        return f"{self.rating:.1f}/5.0 ({self.total_reviews} review{'s' if self.total_reviews != 1 else ''})"

    def add_specialization(self, specialization: str) -> None:
        """
        Add a medical specialization.

        Args:
            specialization: Specialization name to add
        """
        if self.specializations is None:
            self.specializations = []

        if specialization not in self.specializations:
            self.specializations.append(specialization)

    def remove_specialization(self, specialization: str) -> None:
        """
        Remove a medical specialization.

        Args:
            specialization: Specialization name to remove
        """
        if self.specializations and specialization in self.specializations:
            self.specializations.remove(specialization)

    def has_specialization(self, specialization: str) -> bool:
        """
        Check if veterinarian has a specific specialization.

        Args:
            specialization: Specialization name to check

        Returns:
            True if the specialization is present
        """
        return (
            self.specializations is not None and specialization in self.specializations
        )

    def add_service(self, service: str) -> None:
        """
        Add a service to those provided by the veterinarian.

        Args:
            service: Service name to add
        """
        if self.services_provided is None:
            self.services_provided = []

        if service not in self.services_provided:
            self.services_provided.append(service)

    def provides_service(self, service: str) -> bool:
        """
        Check if veterinarian provides a specific service.

        Args:
            service: Service name to check

        Returns:
            True if the service is provided
        """
        return self.services_provided is not None and service in self.services_provided

    def add_species_expertise(self, species: str) -> None:
        """
        Add species expertise.

        Args:
            species: Species name to add
        """
        if self.species_expertise is None:
            self.species_expertise = []

        if species not in self.species_expertise:
            self.species_expertise.append(species)

    def has_species_expertise(self, species: str) -> bool:
        """
        Check if veterinarian has expertise with a specific species.

        Args:
            species: Species name to check

        Returns:
            True if the expertise is present
        """
        return self.species_expertise is not None and species in self.species_expertise

    def set_availability(
        self,
        day_of_week: str,
        start_time: str,
        end_time: str,
        is_available: bool = True,
        break_times: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        Set availability for a specific day.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            is_available: Whether available on this day
            break_times: Optional list of break periods with 'start' and 'end' times
        """
        if self.availability is None:
            self.availability = {}

        day_schedule = {
            "is_available": is_available,
            "start_time": start_time,
            "end_time": end_time,
        }

        if break_times:
            day_schedule["breaks"] = break_times

        self.availability[day_of_week.lower()] = day_schedule

    def is_available_on_day(self, day_of_week: str) -> bool:
        """
        Check if veterinarian is available on a specific day.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)

        Returns:
            True if available on that day
        """
        if not self.availability:
            return False

        day_schedule = self.availability.get(day_of_week.lower())
        if not day_schedule:
            return False

        return bool(day_schedule.get("is_available", False))

    def get_availability_for_day(self, day_of_week: str) -> Optional[Dict[str, Any]]:
        """
        Get availability schedule for a specific day.

        Args:
            day_of_week: Day name (e.g., 'monday', 'tuesday', etc.)

        Returns:
            Dictionary with availability information or None
        """
        if not self.availability:
            return None

        return self.availability.get(day_of_week.lower())

    def update_rating(
        self, new_rating: Union[Decimal, float, int], review_count_change: int = 1
    ) -> None:
        """
        Update the veterinarian's rating with a new review.

        Args:
            new_rating: Rating from the new review (0.0 to 5.0)
            review_count_change: Change in review count (usually 1 for new review)
        """
        # Convert to Decimal if needed
        if not isinstance(new_rating, Decimal):
            new_rating = Decimal(str(new_rating))

        if not (0 <= new_rating <= 5):
            raise ValueError("Rating must be between 0.0 and 5.0")

        # Calculate new average rating
        total_rating_points = self.rating * self.total_reviews
        total_rating_points += new_rating
        self.total_reviews += review_count_change

        if self.total_reviews > 0:
            self.rating = total_rating_points / self.total_reviews
        else:
            self.rating = Decimal("0.0")

    def add_certification(
        self,
        certification_name: str,
        issuing_organization: str,
        date_obtained: date,
        expiry_date: Optional[date] = None,
        certification_number: Optional[str] = None,
    ) -> None:
        """
        Add a professional certification.

        Args:
            certification_name: Name of the certification
            issuing_organization: Organization that issued the certification
            date_obtained: Date when certification was obtained
            expiry_date: Optional expiry date
            certification_number: Optional certification number
        """
        if self.additional_certifications is None:
            self.additional_certifications = []

        certification = {
            "name": certification_name,
            "issuing_organization": issuing_organization,
            "date_obtained": date_obtained.isoformat(),
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "certification_number": certification_number,
            "added_at": datetime.utcnow().isoformat(),
        }

        self.additional_certifications.append(certification)

    def has_certification(self, certification_name: str) -> bool:
        """
        Check if veterinarian has a specific certification.

        Args:
            certification_name: Name of the certification to check

        Returns:
            True if the certification is present and valid
        """
        if not self.additional_certifications:
            return False

        for cert in self.additional_certifications:
            if cert.get("name") == certification_name:
                # Check if certification is still valid
                expiry_date = cert.get("expiry_date")
                if expiry_date:
                    try:
                        expiry = datetime.fromisoformat(expiry_date).date()
                        return expiry >= date.today()
                    except (ValueError, TypeError):
                        continue
                return True

        return False

    def get_expiring_certifications(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get certifications that are expiring within a specified number of days.

        Args:
            days_ahead: Number of days to look ahead for expiring certifications

        Returns:
            List of expiring certifications
        """
        if not self.additional_certifications:
            return []

        from datetime import timedelta

        warning_date = date.today() + timedelta(days=days_ahead)
        expiring = []

        for cert in self.additional_certifications:
            expiry_date = cert.get("expiry_date")
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date).date()
                    if expiry <= warning_date:
                        expiring.append(cert)
                except (ValueError, TypeError):
                    continue

        return expiring

    def update_license_status(
        self, new_status: LicenseStatus, reason: Optional[str] = None
    ) -> None:
        """
        Update the license status.

        Args:
            new_status: New license status
            reason: Optional reason for the status change
        """
        old_status = self.license_status
        self.license_status = new_status

        # If license becomes inactive, update veterinarian status
        if new_status in {
            LicenseStatus.EXPIRED,
            LicenseStatus.SUSPENDED,
            LicenseStatus.REVOKED,
        }:
            self.status = VeterinarianStatus.SUSPENDED
            self.is_accepting_new_patients = False

        # Log status change in bio if reason provided
        if reason:
            status_note = f"License status changed from {old_status.value} to {new_status.value}: {reason}"
            if self.bio:
                self.bio += f"\n\n{status_note}"
            else:
                self.bio = status_note

    def renew_license(self, new_expiry_date: date) -> None:
        """
        Renew the veterinary license.

        Args:
            new_expiry_date: New expiry date for the license
        """
        self.license_status = LicenseStatus.ACTIVE
        self.license_expiry_date = new_expiry_date

        # Reactivate veterinarian if they were suspended due to license issues
        if self.status == VeterinarianStatus.SUSPENDED:
            self.status = VeterinarianStatus.ACTIVE

    def suspend(self, reason: Optional[str] = None) -> None:
        """
        Suspend the veterinarian.

        Args:
            reason: Reason for suspension
        """
        self.status = VeterinarianStatus.SUSPENDED
        self.is_accepting_new_patients = False

        if reason:
            suspension_note = f"Suspended: {reason}"
            if self.bio:
                self.bio += f"\n\n{suspension_note}"
            else:
                self.bio = suspension_note

    def reactivate(self, reason: Optional[str] = None) -> None:
        """
        Reactivate the veterinarian.

        Args:
            reason: Reason for reactivation
        """
        # Only reactivate if license is valid
        if not self.license_is_valid:
            raise ValueError("Cannot reactivate veterinarian with invalid license")

        self.status = VeterinarianStatus.ACTIVE
        self.is_accepting_new_patients = True

        if reason:
            reactivation_note = f"Reactivated: {reason}"
            if self.bio:
                self.bio += f"\n\n{reactivation_note}"
            else:
                self.bio = reactivation_note

    def retire(self, retirement_date: Optional[date] = None) -> None:
        """
        Mark the veterinarian as retired.

        Args:
            retirement_date: Date of retirement (defaults to today)
        """
        self.status = VeterinarianStatus.RETIRED
        self.is_accepting_new_patients = False

        retirement_date = retirement_date or date.today()
        retirement_note = f"Retired on {retirement_date.isoformat()}"

        if self.bio:
            self.bio += f"\n\n{retirement_note}"
        else:
            self.bio = retirement_note

    def get_status_display(self) -> str:
        """Get a human-readable status display."""
        status_display = {
            VeterinarianStatus.ACTIVE: "Active",
            VeterinarianStatus.INACTIVE: "Inactive",
            VeterinarianStatus.ON_LEAVE: "On Leave",
            VeterinarianStatus.SUSPENDED: "Suspended",
            VeterinarianStatus.RETIRED: "Retired",
        }
        return status_display.get(self.status, self.status.value.title())

    def get_license_status_display(self) -> str:
        """Get a human-readable license status display."""
        status_display = {
            LicenseStatus.ACTIVE: "Active",
            LicenseStatus.EXPIRED: "Expired",
            LicenseStatus.SUSPENDED: "Suspended",
            LicenseStatus.REVOKED: "Revoked",
            LicenseStatus.PENDING_RENEWAL: "Pending Renewal",
        }
        return status_display.get(
            self.license_status, self.license_status.value.title()
        )

    def get_employment_type_display(self) -> str:
        """Get a human-readable employment type display."""
        type_display = {
            EmploymentType.FULL_TIME: "Full Time",
            EmploymentType.PART_TIME: "Part Time",
            EmploymentType.CONTRACT: "Contract",
            EmploymentType.LOCUM: "Locum Tenens",
            EmploymentType.OWNER: "Owner",
            EmploymentType.PARTNER: "Partner",
        }
        return type_display.get(
            self.employment_type, self.employment_type.value.title()
        )

    def calculate_capacity_utilization(
        self, current_appointments: int
    ) -> Optional[float]:
        """
        Calculate current capacity utilization as a percentage.

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
        Check if veterinarian is at or over capacity.

        Args:
            current_appointments: Number of current appointments

        Returns:
            True if at or over capacity
        """
        if self.max_daily_appointments is None:
            return False

        return current_appointments >= self.max_daily_appointments
