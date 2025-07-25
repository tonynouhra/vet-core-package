"""
Pet model for the vet-core package.

This module contains the Pet SQLAlchemy model with comprehensive pet data,
medical history tracking, and owner relationships.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class PetSpecies(enum.Enum):
    """
    Enumeration of pet species supported by the platform.

    When using OTHER, provide a description in species_other_description field
    (e.g., 'snake', 'turtle', 'parrot', 'iguana').
    """

    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RABBIT = "rabbit"
    HAMSTER = "hamster"
    GUINEA_PIG = "guinea_pig"
    FERRET = "ferret"
    REPTILE = "reptile"
    FISH = "fish"
    OTHER = "other"


class PetGender(enum.Enum):
    """Enumeration of pet genders."""

    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class PetSize(enum.Enum):
    """Enumeration of pet sizes for classification."""

    EXTRA_SMALL = "extra_small"  # < 5 lbs
    SMALL = "small"  # 5-25 lbs
    MEDIUM = "medium"  # 25-60 lbs
    LARGE = "large"  # 60-100 lbs
    EXTRA_LARGE = "extra_large"  # > 100 lbs


class PetStatus(enum.Enum):
    """Enumeration of pet status in the system."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DECEASED = "deceased"
    LOST = "lost"
    TRANSFERRED = "transferred"


class Pet(BaseModel):
    """
    Pet model with comprehensive pet data and medical history tracking.

    Supports detailed pet information including species, breed, medical history,
    vaccination records, and owner relationships with proper foreign key constraints.
    """

    __tablename__ = "pets"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Pet with default values."""
        # Set default values if not provided
        if "status" not in kwargs:
            kwargs["status"] = PetStatus.ACTIVE
        if "is_spayed_neutered" not in kwargs:
            kwargs["is_spayed_neutered"] = False
        if "is_microchipped" not in kwargs:
            kwargs["is_microchipped"] = False
        if "is_insured" not in kwargs:
            kwargs["is_insured"] = False
        if "gender" not in kwargs:
            kwargs["gender"] = PetGender.UNKNOWN

        super().__init__(**kwargs)

    # Owner relationship - foreign key to User model
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the pet's primary owner",
    )

    # Basic pet information
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Pet's name")

    species: Mapped[PetSpecies] = mapped_column(
        Enum(PetSpecies), nullable=False, index=True, comment="Pet's species"
    )

    species_other_description: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Description when species is 'other' (e.g., 'snake', 'turtle', 'parrot')",
    )

    breed: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="Pet's breed"
    )

    mixed_breed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the pet is a mixed breed",
    )

    # Physical characteristics
    gender: Mapped[PetGender] = mapped_column(
        Enum(PetGender),
        nullable=False,
        default=PetGender.UNKNOWN,
        comment="Pet's gender",
    )

    birth_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Pet's birth date"
    )

    approximate_age_years: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Approximate age in years if birth date unknown"
    )

    approximate_age_months: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Approximate age in months if birth date unknown"
    )

    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),  # Up to 999.99 kg
        nullable=True,
        comment="Pet's weight in kilograms",
    )

    size_category: Mapped[Optional[PetSize]] = mapped_column(
        Enum(PetSize), nullable=True, comment="Pet's size category"
    )

    # Identification and status
    microchip_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
        comment="Microchip identification number",
    )

    registration_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Breed registration number"
    )

    status: Mapped[PetStatus] = mapped_column(
        Enum(PetStatus),
        nullable=False,
        default=PetStatus.ACTIVE,
        index=True,
        comment="Current status of the pet",
    )

    # Medical and care information
    is_spayed_neutered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the pet is spayed or neutered",
    )

    spay_neuter_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Date when pet was spayed or neutered"
    )

    is_microchipped: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the pet has a microchip",
    )

    microchip_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Date when microchip was implanted"
    )

    is_insured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Whether the pet has insurance"
    )

    insurance_provider: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Pet insurance provider name"
    )

    insurance_policy_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Pet insurance policy number"
    )

    # Behavioral and care notes
    temperament: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="Pet's temperament description"
    )

    special_needs: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Special care needs or requirements"
    )

    behavioral_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Behavioral notes and observations"
    )

    # Photo and identification
    profile_photo_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="URL to pet's profile photo"
    )

    additional_photos: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, comment="Array of additional photo URLs"
    )

    # Medical history and vaccination tracking (JSONB fields)
    medical_history: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Comprehensive medical history stored as JSON"
    )

    vaccination_records: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Vaccination history and records stored as JSON array",
    )

    medication_history: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Current and past medications stored as JSON array",
    )

    allergy_information: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Known allergies and reactions stored as JSON array",
    )

    emergency_contact: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Emergency contact information stored as JSON"
    )

    # Veterinary preferences
    preferred_veterinarian_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("veterinarians.id", ondelete="SET NULL"),
        nullable=True,
        comment="UUID of preferred veterinarian",
    )

    preferred_clinic_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("clinics.id", ondelete="SET NULL"),
        nullable=True,
        comment="UUID of preferred clinic",
    )

    # Database constraints and indexes
    __table_args__ = (
        # Check constraints for data integrity
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg > 0", name="ck_pets_weight_positive"
        ),
        CheckConstraint(
            "species != 'other' OR species_other_description IS NOT NULL",
            name="ck_pets_species_other_description_required",
        ),
        CheckConstraint(
            "approximate_age_years IS NULL OR approximate_age_years >= 0",
            name="ck_pets_age_years_non_negative",
        ),
        CheckConstraint(
            "approximate_age_months IS NULL OR (approximate_age_months >= 0 AND approximate_age_months < 12)",
            name="ck_pets_age_months_valid",
        ),
        CheckConstraint(
            "birth_date IS NULL OR birth_date <= CURRENT_DATE",
            name="ck_pets_birth_date_not_future",
        ),
        CheckConstraint(
            "spay_neuter_date IS NULL OR spay_neuter_date <= CURRENT_DATE",
            name="ck_pets_spay_neuter_date_not_future",
        ),
        CheckConstraint(
            "microchip_date IS NULL OR microchip_date <= CURRENT_DATE",
            name="ck_pets_microchip_date_not_future",
        ),
        # Composite indexes for efficient pet queries
        Index("idx_pets_owner_name", "owner_id", "name"),
        Index("idx_pets_owner_species", "owner_id", "species"),
        Index("idx_pets_owner_status", "owner_id", "status"),
        Index("idx_pets_species_breed", "species", "breed"),
        Index("idx_pets_status_species", "status", "species"),
        # Indexes for medical and identification lookups
        Index(
            "idx_pets_microchip_active",
            "microchip_id",
            postgresql_where=(status == PetStatus.ACTIVE),
        ),
        Index("idx_pets_spay_neuter_status", "is_spayed_neutered", "species"),
        Index("idx_pets_insurance_status", "is_insured", "insurance_provider"),
        # Partial indexes for active pets
        Index(
            "idx_pets_active_owner",
            "owner_id",
            postgresql_where=(status == PetStatus.ACTIVE),
        ),
        Index(
            "idx_pets_active_species",
            "species",
            postgresql_where=(status == PetStatus.ACTIVE),
        ),
        # GIN indexes for JSONB fields
        Index(
            "idx_pets_medical_history_gin", "medical_history", postgresql_using="gin"
        ),
        Index(
            "idx_pets_vaccination_records_gin",
            "vaccination_records",
            postgresql_using="gin",
        ),
        Index(
            "idx_pets_medication_history_gin",
            "medication_history",
            postgresql_using="gin",
        ),
        Index(
            "idx_pets_allergy_information_gin",
            "allergy_information",
            postgresql_using="gin",
        ),
        # Full-text search indexes for names and notes
        Index(
            "idx_pets_name_search",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        # Index for species other description
        Index("idx_pets_species_other_description", "species_other_description"),
    )

    # Relationships
    owner = relationship("User", back_populates="pets")
    appointments = relationship("Appointment", back_populates="pet")

    def __repr__(self) -> str:
        """String representation of the Pet model."""
        return f"<Pet(id={self.id}, name='{self.name}', species='{self.species.value}', owner_id={self.owner_id})>"

    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the pet."""
        return self.name

    @property
    def is_active(self) -> bool:
        """Check if the pet is active."""
        return self.status == PetStatus.ACTIVE and not self.is_deleted

    @property
    def age_in_years(self) -> Optional[int]:
        """Calculate pet's age in years."""
        if self.birth_date:
            today = date.today()
            age = today.year - self.birth_date.year
            # Adjust if birthday hasn't occurred this year
            if today.month < self.birth_date.month or (
                today.month == self.birth_date.month and today.day < self.birth_date.day
            ):
                age -= 1
            return max(0, age)
        elif self.approximate_age_years is not None:
            return self.approximate_age_years
        return None

    @property
    def age_display(self) -> str:
        """Get a human-readable age display."""
        if self.birth_date:
            age_years = self.age_in_years
            if age_years == 0:
                # Calculate months for young pets
                today = date.today()
                months = (
                    (today.year - self.birth_date.year) * 12
                    + today.month
                    - self.birth_date.month
                )
                if today.day < self.birth_date.day:
                    months -= 1
                months = max(0, months)
                return f"{months} month{'s' if months != 1 else ''}"
            else:
                return f"{age_years} year{'s' if age_years != 1 else ''}"
        elif self.approximate_age_years is not None:
            years = self.approximate_age_years
            months = self.approximate_age_months or 0
            if years == 0 and months > 0:
                return f"~{months} month{'s' if months != 1 else ''}"
            elif years > 0 and months > 0:
                return f"~{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
            elif years > 0:
                return f"~{years} year{'s' if years != 1 else ''}"
        return "Unknown"

    @property
    def weight_display(self) -> str:
        """Get a human-readable weight display in kg."""
        if self.weight_kg:
            return f"{self.weight_kg} kg"
        return "Unknown"

    @property
    def weight_display_lbs(self) -> str:
        """Get a human-readable weight display in lbs."""
        if self.weight_kg:
            weight_lbs = self.kg_to_lbs(self.weight_kg)
            return f"{weight_lbs:.1f} lbs"
        return "Unknown"

    @staticmethod
    def kg_to_lbs(weight_kg: Decimal) -> Decimal:
        """Convert weight from kilograms to pounds."""
        return weight_kg * Decimal("2.20462")

    @staticmethod
    def lbs_to_kg(weight_lbs: Decimal) -> Decimal:
        """Convert weight from pounds to kilograms."""
        return weight_lbs / Decimal("2.20462")

    @property
    def breed_display(self) -> str:
        """Get a display-friendly breed name."""
        if self.breed:
            if self.mixed_breed:
                return f"{self.breed} Mix"
            return self.breed
        elif self.mixed_breed:
            return "Mixed Breed"
        return "Unknown"

    @property
    def species_display(self) -> str:
        """Get a display-friendly species name."""
        if self.species == PetSpecies.OTHER and self.species_other_description:
            return self.species_other_description.title()
        else:
            return self.species.value.replace("_", " ").title()

    def set_other_species(self, description: str) -> None:
        """
        Set the species to 'other' with a custom description.

        Args:
            description: Description of the species (e.g., 'snake', 'turtle')
        """
        if not description or not description.strip():
            raise ValueError("Description is required when setting species to 'other'")
        self.species = PetSpecies.OTHER
        self.species_other_description = description.strip().lower()

    def validate_species_description(self) -> bool:
        """
        Validate that if species is 'other', a description is provided.

        Returns:
            True if valid, False otherwise
        """
        if self.species == PetSpecies.OTHER:
            return bool(
                self.species_other_description
                and self.species_other_description.strip()
            )
        return True

    def is_due_for_vaccination(self, vaccine_type: str) -> bool:
        """
        Check if pet is due for a specific vaccination.

        Args:
            vaccine_type: Type of vaccine to check

        Returns:
            True if vaccination is due or overdue
        """
        if not self.vaccination_records:
            return True

        # Find the most recent vaccination of this type
        latest_vaccination = None
        for record in self.vaccination_records:
            if record.get("vaccine_type") == vaccine_type:
                vaccination_date = record.get("date")
                if vaccination_date:
                    if (
                        latest_vaccination is None
                        or vaccination_date > latest_vaccination
                    ):
                        latest_vaccination = vaccination_date

        if not latest_vaccination:
            return True

        # Check if vaccination is due based on type and species
        # This is a simplified check - in practice, you'd have more complex logic
        try:
            last_vaccination = datetime.fromisoformat(latest_vaccination).date()
            today = date.today()
            days_since = (today - last_vaccination).days

            # Basic vaccination schedules (simplified)
            if vaccine_type.lower() in ["rabies"]:
                return days_since > 365  # Annual
            elif vaccine_type.lower() in ["dhpp", "fvrcp"]:
                return days_since > 365  # Annual
            else:
                return days_since > 365  # Default to annual

        except (ValueError, TypeError):
            return True

    def add_vaccination_record(
        self,
        vaccine_type: str,
        date_administered: date,
        veterinarian: str,
        batch_number: Optional[str] = None,
        next_due_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> None:
        """
        Add a vaccination record to the pet's history.

        Args:
            vaccine_type: Type of vaccine administered
            date_administered: Date the vaccine was given
            veterinarian: Name of administering veterinarian
            batch_number: Vaccine batch number
            next_due_date: When the next dose is due
            notes: Additional notes about the vaccination
        """
        if self.vaccination_records is None:
            self.vaccination_records = []

        record = {
            "vaccine_type": vaccine_type,
            "date": date_administered.isoformat(),
            "veterinarian": veterinarian,
            "batch_number": batch_number,
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
            "notes": notes,
            "recorded_at": datetime.utcnow().isoformat(),
        }

        self.vaccination_records.append(record)

    def add_medical_record(
        self,
        record_type: str,
        description: str,
        date_recorded: date,
        veterinarian: Optional[str] = None,
        diagnosis: Optional[str] = None,
        treatment: Optional[str] = None,
        follow_up_needed: bool = False,
    ) -> None:
        """
        Add a medical record to the pet's history.

        Args:
            record_type: Type of medical record (checkup, illness, injury, etc.)
            description: Description of the medical event
            date_recorded: Date of the medical event
            veterinarian: Name of attending veterinarian
            diagnosis: Medical diagnosis
            treatment: Treatment provided
            follow_up_needed: Whether follow-up is required
        """
        if self.medical_history is None:
            self.medical_history = {"records": []}
        elif "records" not in self.medical_history:
            self.medical_history["records"] = []

        record = {
            "type": record_type,
            "description": description,
            "date": date_recorded.isoformat(),
            "veterinarian": veterinarian,
            "diagnosis": diagnosis,
            "treatment": treatment,
            "follow_up_needed": follow_up_needed,
            "recorded_at": datetime.utcnow().isoformat(),
        }

        self.medical_history["records"].append(record)

    def add_allergy(
        self,
        allergen: str,
        reaction: str,
        severity: str = "unknown",
        date_discovered: Optional[date] = None,
    ) -> None:
        """
        Add an allergy to the pet's allergy information.

        Args:
            allergen: The substance causing the allergic reaction
            reaction: Description of the allergic reaction
            severity: Severity level (mild, moderate, severe, unknown)
            date_discovered: When the allergy was discovered
        """
        if self.allergy_information is None:
            self.allergy_information = []

        allergy = {
            "allergen": allergen,
            "reaction": reaction,
            "severity": severity,
            "date_discovered": date_discovered.isoformat() if date_discovered else None,
            "recorded_at": datetime.utcnow().isoformat(),
        }

        self.allergy_information.append(allergy)

    def update_weight(
        self, weight_kg: Decimal, recorded_by: Optional[str] = None
    ) -> None:
        """
        Update the pet's weight and add to weight history.

        Args:
            weight_kg: New weight in kilograms
            recorded_by: Who recorded the weight
        """
        # Store previous weight in medical history
        if self.weight_kg and self.medical_history:
            if "weight_history" not in self.medical_history:
                self.medical_history["weight_history"] = []

            weight_record = {
                "weight_kg": float(self.weight_kg),
                "date": datetime.utcnow().isoformat(),
                "recorded_by": recorded_by,
            }
            self.medical_history["weight_history"].append(weight_record)

        # Update current weight
        self.weight_kg = weight_kg

        # Update size category based on weight (for dogs - simplified logic using kg)
        if self.species == PetSpecies.DOG and weight_kg:
            if weight_kg < 2.3:  # < 5 lbs
                self.size_category = PetSize.EXTRA_SMALL
            elif weight_kg < 11.3:  # < 25 lbs
                self.size_category = PetSize.SMALL
            elif weight_kg < 27.2:  # < 60 lbs
                self.size_category = PetSize.MEDIUM
            elif weight_kg < 45.4:  # < 100 lbs
                self.size_category = PetSize.LARGE
            else:
                self.size_category = PetSize.EXTRA_LARGE

    def update_weight_from_lbs(
        self, weight_lbs: Decimal, recorded_by: Optional[str] = None
    ) -> None:
        """
        Update the pet's weight from pounds (converts to kg internally).

        Args:
            weight_lbs: New weight in pounds
            recorded_by: Who recorded the weight
        """
        weight_kg = self.lbs_to_kg(weight_lbs)
        self.update_weight(weight_kg, recorded_by)

    def mark_deceased(
        self, date_of_death: Optional[date] = None, cause: Optional[str] = None
    ) -> None:
        """
        Mark the pet as deceased.

        Args:
            date_of_death: Date the pet passed away
            cause: Cause of death
        """
        self.status = PetStatus.DECEASED

        if self.medical_history is None:
            self.medical_history = {}

        self.medical_history["deceased"] = {
            "date_of_death": (
                date_of_death.isoformat() if date_of_death else date.today().isoformat()
            ),
            "cause": cause,
            "recorded_at": datetime.utcnow().isoformat(),
        }

    def transfer_ownership(
        self, new_owner_id: uuid.UUID, transfer_reason: Optional[str] = None
    ) -> None:
        """
        Transfer pet ownership to a new owner.

        Args:
            new_owner_id: UUID of the new owner
            transfer_reason: Reason for the transfer
        """
        old_owner_id = self.owner_id
        self.owner_id = new_owner_id

        if self.medical_history is None:
            self.medical_history = {}

        if "ownership_history" not in self.medical_history:
            self.medical_history["ownership_history"] = []

        transfer_record = {
            "previous_owner_id": str(old_owner_id),
            "new_owner_id": str(new_owner_id),
            "transfer_date": datetime.utcnow().isoformat(),
            "reason": transfer_reason,
        }

        self.medical_history["ownership_history"].append(transfer_record)

    def get_latest_vaccination(self, vaccine_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent vaccination record for a specific vaccine type.

        Args:
            vaccine_type: Type of vaccine to search for

        Returns:
            Most recent vaccination record or None
        """
        if not self.vaccination_records:
            return None

        latest = None
        latest_date = None

        for record in self.vaccination_records:
            if record.get("vaccine_type") == vaccine_type:
                record_date = record.get("date")
                if record_date and (latest_date is None or record_date > latest_date):
                    latest = record
                    latest_date = record_date

        return latest

    def get_medical_records_by_type(self, record_type: str) -> List[Dict[str, Any]]:
        """
        Get all medical records of a specific type.

        Args:
            record_type: Type of medical record to retrieve

        Returns:
            List of matching medical records
        """
        if not self.medical_history or "records" not in self.medical_history:
            return []

        return [
            record
            for record in self.medical_history["records"]
            if record.get("type") == record_type
        ]
