"""
Pet Pydantic schemas for API validation and serialization.

This module contains Pydantic schemas for Pet model validation,
including create, update, and response schemas with medical data validation.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.pet import PetGender, PetSize, PetSpecies, PetStatus


class VaccinationRecordSchema(BaseModel):
    """Schema for vaccination records."""

    model_config = ConfigDict(from_attributes=True)

    vaccine_type: str = Field(..., description="Type of vaccine administered")
    date: str = Field(..., description="Date administered (ISO format)")
    veterinarian: str = Field(..., description="Name of administering veterinarian")
    batch_number: Optional[str] = Field(None, description="Vaccine batch number")
    next_due_date: Optional[str] = Field(None, description="Next due date (ISO format)")
    notes: Optional[str] = Field(None, description="Additional notes")

    @field_validator("vaccine_type")
    @classmethod
    def validate_vaccine_type(cls, v: str) -> str:
        """Validate vaccine type."""
        if not v or not v.strip():
            raise ValueError("Vaccine type is required")
        return v.strip().title()

    @field_validator("date", "next_due_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v is None:
            return v

        try:
            # Validate ISO datetime format - must include time component
            parsed_date = datetime.fromisoformat(v.replace("Z", "+00:00"))
            # Check that it's a full datetime format (has time component)
            if "T" not in v:
                raise ValueError(
                    "Date must include time component (ISO datetime format)"
                )
            return v
        except ValueError:
            raise ValueError(
                "Date must be in ISO datetime format (e.g., '2023-01-15T10:00:00')"
            )

    @field_validator("veterinarian")
    @classmethod
    def validate_veterinarian(cls, v: str) -> str:
        """Validate veterinarian name."""
        if not v or not v.strip():
            raise ValueError("Veterinarian name is required")
        return v.strip()


class MedicalRecordSchema(BaseModel):
    """Schema for medical records."""

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(..., description="Type of medical record")
    description: str = Field(..., description="Description of the medical event")
    date: str = Field(..., description="Date of the medical event (ISO format)")
    veterinarian: Optional[str] = Field(
        None, description="Name of attending veterinarian"
    )
    diagnosis: Optional[str] = Field(None, description="Medical diagnosis")
    treatment: Optional[str] = Field(None, description="Treatment provided")
    follow_up_needed: bool = Field(False, description="Whether follow-up is required")

    @field_validator("type", "description")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required string fields."""
        if not v or not v.strip():
            raise ValueError("Field is required")
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Date must be in ISO format")


class AllergySchema(BaseModel):
    """Schema for allergy information."""

    model_config = ConfigDict(from_attributes=True)

    allergen: str = Field(
        ..., description="The substance causing the allergic reaction"
    )
    reaction: str = Field(..., description="Description of the allergic reaction")
    severity: str = Field("unknown", description="Severity level")
    date_discovered: Optional[str] = Field(
        None, description="When the allergy was discovered"
    )

    @field_validator("allergen", "reaction")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required string fields."""
        if not v or not v.strip():
            raise ValueError("Field is required")
        return v.strip()

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        allowed_severities = {"mild", "moderate", "severe", "unknown"}
        if v.lower() not in allowed_severities:
            raise ValueError(
                f"Severity must be one of: {', '.join(allowed_severities)}"
            )
        return v.lower()

    @field_validator("date_discovered")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Date must be in ISO format")


class EmergencyContactSchema(BaseModel):
    """Schema for emergency contact information."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Emergency contact name")
    phone: str = Field(..., description="Emergency contact phone number")
    relationship: Optional[str] = Field(None, description="Relationship to pet owner")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate contact name."""
        if not v or not v.strip():
            raise ValueError("Emergency contact name is required")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number."""
        if not v or not v.strip():
            raise ValueError("Emergency contact phone is required")

        # Remove all non-digit characters for validation
        digits_only = re.sub(r"\D", "", v)

        # Check if it's a valid length (10-15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits")

        return v.strip()


class PetBase(BaseModel):
    """Base Pet schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    name: str = Field(..., description="Pet's name", min_length=1, max_length=100)
    species: PetSpecies = Field(..., description="Pet's species")
    species_other_description: Optional[str] = Field(
        None, description="Description when species is 'other'", max_length=100
    )
    breed: Optional[str] = Field(None, description="Pet's breed", max_length=100)
    mixed_breed: bool = Field(False, description="Whether the pet is a mixed breed")
    gender: PetGender = Field(PetGender.UNKNOWN, description="Pet's gender")
    birth_date: Optional[date] = Field(None, description="Pet's birth date")
    approximate_age_years: Optional[int] = Field(
        None, description="Approximate age in years if birth date unknown", ge=0, le=50
    )
    approximate_age_months: Optional[int] = Field(
        None, description="Approximate age in months if birth date unknown", ge=0, lt=12
    )
    weight_kg: Optional[Decimal] = Field(
        None, description="Pet's weight in kilograms", gt=0, le=Decimal("999.99")
    )
    size_category: Optional[PetSize] = Field(None, description="Pet's size category")
    microchip_id: Optional[str] = Field(
        None, description="Microchip identification number", max_length=50
    )
    registration_number: Optional[str] = Field(
        None, description="Breed registration number", max_length=100
    )
    is_spayed_neutered: bool = Field(
        False, description="Whether the pet is spayed or neutered"
    )
    spay_neuter_date: Optional[date] = Field(
        None, description="Date when pet was spayed or neutered"
    )
    is_microchipped: bool = Field(False, description="Whether the pet has a microchip")
    microchip_date: Optional[date] = Field(
        None, description="Date when microchip was implanted"
    )
    is_insured: bool = Field(False, description="Whether the pet has insurance")
    insurance_provider: Optional[str] = Field(
        None, description="Pet insurance provider name", max_length=100
    )
    insurance_policy_number: Optional[str] = Field(
        None, description="Pet insurance policy number", max_length=100
    )
    temperament: Optional[str] = Field(
        None, description="Pet's temperament description", max_length=200
    )
    special_needs: Optional[str] = Field(
        None, description="Special care needs or requirements"
    )
    behavioral_notes: Optional[str] = Field(
        None, description="Behavioral notes and observations"
    )
    profile_photo_url: Optional[str] = Field(
        None, description="URL to pet's profile photo", max_length=500
    )
    additional_photos: Optional[List[str]] = Field(
        None, description="Array of additional photo URLs"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate pet name."""
        if not v or not v.strip():
            raise ValueError("Pet name is required")

        # Allow letters, numbers, spaces, hyphens, apostrophes, and periods
        if not re.match(r"^[a-zA-Z0-9\s\-'.]+$", v):
            raise ValueError(
                "Pet name can only contain letters, numbers, spaces, hyphens, apostrophes, and periods"
            )

        return v.strip()

    @field_validator("species_other_description")
    @classmethod
    def validate_species_other_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate species other description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic validation for species description
            if not re.match(r"^[a-zA-Z\s\-']+$", v):
                raise ValueError(
                    "Species description can only contain letters, spaces, hyphens, and apostrophes"
                )

        return v

    @field_validator("breed")
    @classmethod
    def validate_breed(cls, v: Optional[str]) -> Optional[str]:
        """Validate breed."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Allow letters, numbers, spaces, hyphens, apostrophes, and periods
            if not re.match(r"^[a-zA-Z0-9\s\-'.]+$", v):
                raise ValueError(
                    "Breed can only contain letters, numbers, spaces, hyphens, apostrophes, and periods"
                )

        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate birth date."""
        if v is not None and v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v

    @field_validator("spay_neuter_date", "microchip_date")
    @classmethod
    def validate_procedure_dates(cls, v: Optional[date]) -> Optional[date]:
        """Validate procedure dates."""
        if v is not None and v > date.today():
            raise ValueError("Procedure date cannot be in the future")
        return v

    @field_validator("microchip_id")
    @classmethod
    def validate_microchip_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate microchip ID."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Microchip IDs are typically 15 alphanumeric characters
            if not re.match(r"^[0-9A-Za-z]+$", v):
                raise ValueError("Microchip ID can only contain numbers and letters")

            if len(v) != 15:
                raise ValueError("Microchip ID must be exactly 15 characters")

        return v

    @field_validator("additional_photos")
    @classmethod
    def validate_additional_photos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate additional photos URLs."""
        if v is not None:
            if len(v) > 10:  # Reasonable limit
                raise ValueError("Maximum 10 additional photos allowed")

            for url in v:
                if not url or not url.strip():
                    raise ValueError("Photo URLs cannot be empty")
                if len(url) > 500:
                    raise ValueError("Photo URL too long")

        return v

    @model_validator(mode="after")
    def validate_species_other_consistency(self) -> "PetBase":
        """Validate that species 'other' has description."""
        # Handle both enum object and string value comparisons
        species_value = (
            self.species.value if isinstance(self.species, PetSpecies) else self.species
        )
        if (
            species_value == PetSpecies.OTHER.value
            and not self.species_other_description
        ):
            raise ValueError(
                "Species other description is required when species is 'other'"
            )
        return self

    @model_validator(mode="after")
    def validate_microchip_consistency(self) -> "PetBase":
        """Validate microchip consistency."""
        if self.is_microchipped and not self.microchip_id:
            raise ValueError(
                "Microchip ID is required when pet is marked as microchipped"
            )
        return self

    @model_validator(mode="after")
    def validate_insurance_consistency(self) -> "PetBase":
        """Validate insurance consistency."""
        if self.is_insured and not self.insurance_provider:
            raise ValueError(
                "Insurance provider is required when pet is marked as insured"
            )
        return self

    @model_validator(mode="after")
    def validate_age_consistency(self) -> "PetBase":
        """Validate age information consistency."""
        if self.birth_date and (
            self.approximate_age_years is not None
            or self.approximate_age_months is not None
        ):
            raise ValueError("Cannot specify both birth date and approximate age")
        return self


class PetCreate(PetBase):
    """Schema for creating a new pet."""

    owner_id: UUID = Field(..., description="UUID of the pet's primary owner")
    status: PetStatus = Field(PetStatus.ACTIVE, description="Pet's status")
    vaccination_records: Optional[List[VaccinationRecordSchema]] = Field(
        None, description="Vaccination history and records"
    )
    allergy_information: Optional[List[AllergySchema]] = Field(
        None, description="Known allergies and reactions"
    )
    emergency_contact: Optional[EmergencyContactSchema] = Field(
        None, description="Emergency contact information"
    )
    preferred_veterinarian_id: Optional[UUID] = Field(
        None, description="UUID of preferred veterinarian"
    )
    preferred_clinic_id: Optional[UUID] = Field(
        None, description="UUID of preferred clinic"
    )

    @field_validator("vaccination_records")
    @classmethod
    def validate_vaccination_records(
        cls, v: Optional[List[VaccinationRecordSchema]]
    ) -> Optional[List[VaccinationRecordSchema]]:
        """Validate vaccination records."""
        if v is not None and len(v) > 50:  # Reasonable limit
            raise ValueError("Maximum 50 vaccination records allowed")
        return v

    @field_validator("allergy_information")
    @classmethod
    def validate_allergy_information(
        cls, v: Optional[List[AllergySchema]]
    ) -> Optional[List[AllergySchema]]:
        """Validate allergy information."""
        if v is not None and len(v) > 20:  # Reasonable limit
            raise ValueError("Maximum 20 allergy records allowed")
        return v


class PetUpdate(BaseModel):
    """Schema for updating an existing pet."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    name: Optional[str] = Field(
        None, description="Pet's name", min_length=1, max_length=100
    )
    species: Optional[PetSpecies] = Field(None, description="Pet's species")
    species_other_description: Optional[str] = Field(
        None, description="Description when species is 'other'", max_length=100
    )
    breed: Optional[str] = Field(None, description="Pet's breed", max_length=100)
    mixed_breed: Optional[bool] = Field(
        None, description="Whether the pet is a mixed breed"
    )
    gender: Optional[PetGender] = Field(None, description="Pet's gender")
    birth_date: Optional[date] = Field(None, description="Pet's birth date")
    approximate_age_years: Optional[int] = Field(
        None, description="Approximate age in years if birth date unknown", ge=0, le=50
    )
    approximate_age_months: Optional[int] = Field(
        None, description="Approximate age in months if birth date unknown", ge=0, lt=12
    )
    weight_kg: Optional[Decimal] = Field(
        None, description="Pet's weight in kilograms", gt=0, le=Decimal("999.99")
    )
    size_category: Optional[PetSize] = Field(None, description="Pet's size category")
    microchip_id: Optional[str] = Field(
        None, description="Microchip identification number", max_length=50
    )
    registration_number: Optional[str] = Field(
        None, description="Breed registration number", max_length=100
    )
    status: Optional[PetStatus] = Field(None, description="Pet's status")
    is_spayed_neutered: Optional[bool] = Field(
        None, description="Whether the pet is spayed or neutered"
    )
    spay_neuter_date: Optional[date] = Field(
        None, description="Date when pet was spayed or neutered"
    )
    is_microchipped: Optional[bool] = Field(
        None, description="Whether the pet has a microchip"
    )
    microchip_date: Optional[date] = Field(
        None, description="Date when microchip was implanted"
    )
    is_insured: Optional[bool] = Field(
        None, description="Whether the pet has insurance"
    )
    insurance_provider: Optional[str] = Field(
        None, description="Pet insurance provider name", max_length=100
    )
    insurance_policy_number: Optional[str] = Field(
        None, description="Pet insurance policy number", max_length=100
    )
    temperament: Optional[str] = Field(
        None, description="Pet's temperament description", max_length=200
    )
    special_needs: Optional[str] = Field(
        None, description="Special care needs or requirements"
    )
    behavioral_notes: Optional[str] = Field(
        None, description="Behavioral notes and observations"
    )
    profile_photo_url: Optional[str] = Field(
        None, description="URL to pet's profile photo", max_length=500
    )
    additional_photos: Optional[List[str]] = Field(
        None, description="Array of additional photo URLs"
    )
    vaccination_records: Optional[List[VaccinationRecordSchema]] = Field(
        None, description="Vaccination history and records"
    )
    allergy_information: Optional[List[AllergySchema]] = Field(
        None, description="Known allergies and reactions"
    )
    emergency_contact: Optional[EmergencyContactSchema] = Field(
        None, description="Emergency contact information"
    )
    preferred_veterinarian_id: Optional[UUID] = Field(
        None, description="UUID of preferred veterinarian"
    )
    preferred_clinic_id: Optional[UUID] = Field(
        None, description="UUID of preferred clinic"
    )

    # Define validators directly for PetUpdate to avoid ValidationInfo issues
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate pet name."""
        if v is not None:
            return PetBase.validate_name(v)
        return v

    @field_validator("species_other_description")
    @classmethod
    def validate_species_other_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate species other description."""
        if v is not None:
            return PetBase.validate_species_other_description(v)
        return v

    @field_validator("breed")
    @classmethod
    def validate_breed(cls, v: Optional[str]) -> Optional[str]:
        """Validate breed."""
        if v is not None:
            return PetBase.validate_breed(v)
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate birth date."""
        if v is not None:
            return PetBase.validate_birth_date(v)
        return v

    @field_validator("spay_neuter_date", "microchip_date")
    @classmethod
    def validate_procedure_dates(cls, v: Optional[date]) -> Optional[date]:
        """Validate procedure dates."""
        if v is not None:
            return PetBase.validate_procedure_dates(v)
        return v

    @field_validator("microchip_id")
    @classmethod
    def validate_microchip_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate microchip ID."""
        if v is not None:
            return PetBase.validate_microchip_id(v)
        return v

    @field_validator("additional_photos")
    @classmethod
    def validate_additional_photos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate additional photos."""
        if v is not None:
            return PetBase.validate_additional_photos(v)
        return v

    @field_validator("vaccination_records")
    @classmethod
    def validate_vaccination_records(
        cls, v: Optional[List[VaccinationRecordSchema]]
    ) -> Optional[List[VaccinationRecordSchema]]:
        """Validate vaccination records."""
        if v is not None:
            return PetCreate.validate_vaccination_records(v)
        return v

    @field_validator("allergy_information")
    @classmethod
    def validate_allergy_information(
        cls, v: Optional[List[AllergySchema]]
    ) -> Optional[List[AllergySchema]]:
        """Validate allergy information."""
        if v is not None:
            return PetCreate.validate_allergy_information(v)
        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "PetUpdate":
        """Ensure at least one field is provided for update."""
        # Get all field names except the model_config
        field_names = [name for name in self.model_fields.keys()]
        field_values = [getattr(self, name) for name in field_names]

        if not any(value is not None for value in field_values):
            raise ValueError("At least one field must be provided for update")
        return self


class PetResponse(BaseModel):
    """Schema for pet response data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

    id: UUID = Field(..., description="Pet's unique identifier")
    owner_id: UUID = Field(..., description="Owner's unique identifier")
    name: str = Field(..., description="Pet's name")
    species: PetSpecies = Field(..., description="Pet's species")
    species_other_description: Optional[str] = Field(
        None, description="Species description for 'other'"
    )
    breed: Optional[str] = Field(None, description="Pet's breed")
    mixed_breed: bool = Field(..., description="Whether the pet is a mixed breed")
    gender: PetGender = Field(..., description="Pet's gender")
    birth_date: Optional[date] = Field(None, description="Pet's birth date")
    approximate_age_years: Optional[int] = Field(
        None, description="Approximate age in years"
    )
    approximate_age_months: Optional[int] = Field(
        None, description="Approximate age in months"
    )
    weight_kg: Optional[Decimal] = Field(None, description="Pet's weight in kilograms")
    size_category: Optional[PetSize] = Field(None, description="Pet's size category")
    microchip_id: Optional[str] = Field(
        None, description="Microchip identification number"
    )
    registration_number: Optional[str] = Field(
        None, description="Breed registration number"
    )
    status: PetStatus = Field(..., description="Pet's status")
    is_spayed_neutered: bool = Field(
        ..., description="Whether the pet is spayed or neutered"
    )
    spay_neuter_date: Optional[date] = Field(
        None, description="Date when pet was spayed or neutered"
    )
    is_microchipped: bool = Field(..., description="Whether the pet has a microchip")
    microchip_date: Optional[date] = Field(
        None, description="Date when microchip was implanted"
    )
    is_insured: bool = Field(..., description="Whether the pet has insurance")
    insurance_provider: Optional[str] = Field(
        None, description="Pet insurance provider name"
    )
    insurance_policy_number: Optional[str] = Field(
        None, description="Pet insurance policy number"
    )
    temperament: Optional[str] = Field(
        None, description="Pet's temperament description"
    )
    special_needs: Optional[str] = Field(
        None, description="Special care needs or requirements"
    )
    behavioral_notes: Optional[str] = Field(
        None, description="Behavioral notes and observations"
    )
    profile_photo_url: Optional[str] = Field(
        None, description="URL to pet's profile photo"
    )
    additional_photos: Optional[List[str]] = Field(
        None, description="Array of additional photo URLs"
    )
    vaccination_records: Optional[List[VaccinationRecordSchema]] = Field(
        None, description="Vaccination records"
    )
    allergy_information: Optional[List[AllergySchema]] = Field(
        None, description="Allergy information"
    )
    emergency_contact: Optional[EmergencyContactSchema] = Field(
        None, description="Emergency contact"
    )
    preferred_veterinarian_id: Optional[UUID] = Field(
        None, description="Preferred veterinarian ID"
    )
    preferred_clinic_id: Optional[UUID] = Field(None, description="Preferred clinic ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PetListResponse(BaseModel):
    """Schema for paginated pet list responses."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(..., description="Pet's unique identifier")
    owner_id: UUID = Field(..., description="Owner's unique identifier")
    name: str = Field(..., description="Pet's name")
    species: PetSpecies = Field(..., description="Pet's species")
    breed: Optional[str] = Field(None, description="Pet's breed")
    gender: PetGender = Field(..., description="Pet's gender")
    status: PetStatus = Field(..., description="Pet's status")
    profile_photo_url: Optional[str] = Field(None, description="Profile photo URL")
    created_at: datetime = Field(..., description="Creation timestamp")


class PetMedicalHistoryUpdate(BaseModel):
    """Schema for updating pet medical history."""

    model_config = ConfigDict(validate_assignment=True)

    medical_records: List[MedicalRecordSchema] = Field(
        ..., description="Medical records to add"
    )

    @field_validator("medical_records")
    @classmethod
    def validate_medical_records(
        cls, v: List[MedicalRecordSchema]
    ) -> List[MedicalRecordSchema]:
        """Validate medical records."""
        if len(v) == 0:
            raise ValueError("At least one medical record is required")
        if len(v) > 10:  # Reasonable limit per update
            raise ValueError("Maximum 10 medical records per update")
        return v


class PetVaccinationUpdate(BaseModel):
    """Schema for updating pet vaccination records."""

    model_config = ConfigDict(validate_assignment=True)

    vaccination_records: List[VaccinationRecordSchema] = Field(
        ..., description="Vaccination records to add"
    )

    @field_validator("vaccination_records")
    @classmethod
    def validate_vaccination_records(
        cls, v: List[VaccinationRecordSchema]
    ) -> List[VaccinationRecordSchema]:
        """Validate vaccination records."""
        if len(v) == 0:
            raise ValueError("At least one vaccination record is required")
        if len(v) > 5:  # Reasonable limit per update
            raise ValueError("Maximum 5 vaccination records per update")
        return v


class PetWeightUpdate(BaseModel):
    """Schema for updating pet weight."""

    model_config = ConfigDict(validate_assignment=True)

    weight_kg: Decimal = Field(
        ..., description="Pet's new weight in kilograms", gt=0, le=Decimal("999.99")
    )
    recorded_by: Optional[str] = Field(None, description="Who recorded the weight")

    @field_validator("recorded_by")
    @classmethod
    def validate_recorded_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate recorded by field."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
