"""
Tests for Pet Pydantic schemas.

This module contains comprehensive tests for Pet schema validation,
including create, update, and response schemas with various edge cases.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from vet_core.models.pet import PetGender, PetSize, PetSpecies, PetStatus
from vet_core.schemas.pet import (
    AllergySchema,
    EmergencyContactSchema,
    MedicalRecordSchema,
    PetBase,
    PetCreate,
    PetListResponse,
    PetMedicalHistoryUpdate,
    PetResponse,
    PetUpdate,
    PetVaccinationUpdate,
    PetWeightUpdate,
    VaccinationRecordSchema,
)


class TestVaccinationRecordSchema:
    """Test VaccinationRecordSchema validation."""

    def test_valid_vaccination_record(self):
        """Test creating a valid vaccination record."""
        record_data = {
            "vaccine_type": "rabies",
            "date": "2023-01-15T10:00:00",
            "veterinarian": "Dr. Smith",
            "batch_number": "VAC123456",
            "next_due_date": "2024-01-15T10:00:00",
            "notes": "No adverse reactions",
        }

        record = VaccinationRecordSchema(**record_data)
        assert record.vaccine_type == "Rabies"  # Should be title-cased
        assert record.date == "2023-01-15T10:00:00"
        assert record.veterinarian == "Dr. Smith"
        assert record.batch_number == "VAC123456"
        assert record.next_due_date == "2024-01-15T10:00:00"
        assert record.notes == "No adverse reactions"

    def test_required_fields(self):
        """Test that required fields are validated."""
        # Missing vaccine_type
        with pytest.raises(ValidationError):
            VaccinationRecordSchema(
                date="2023-01-15T10:00:00", veterinarian="Dr. Smith"
            )

        # Missing date
        with pytest.raises(ValidationError):
            VaccinationRecordSchema(vaccine_type="rabies", veterinarian="Dr. Smith")

        # Missing veterinarian
        with pytest.raises(ValidationError):
            VaccinationRecordSchema(vaccine_type="rabies", date="2023-01-15T10:00:00")

    def test_date_validation(self):
        """Test date format validation."""
        base_data = {"vaccine_type": "rabies", "veterinarian": "Dr. Smith"}

        # Valid ISO date
        record = VaccinationRecordSchema(date="2023-01-15T10:00:00", **base_data)
        assert record.date == "2023-01-15T10:00:00"

        # Valid ISO date with timezone
        record = VaccinationRecordSchema(date="2023-01-15T10:00:00Z", **base_data)
        assert record.date == "2023-01-15T10:00:00Z"

        # Invalid date format
        with pytest.raises(ValidationError):
            VaccinationRecordSchema(date="2023-01-15", **base_data)

        with pytest.raises(ValidationError):
            VaccinationRecordSchema(date="invalid-date", **base_data)


class TestMedicalRecordSchema:
    """Test MedicalRecordSchema validation."""

    def test_valid_medical_record(self):
        """Test creating a valid medical record."""
        record_data = {
            "type": "checkup",
            "description": "Annual wellness exam",
            "date": "2023-06-10T14:30:00",
            "veterinarian": "Dr. Johnson",
            "diagnosis": "Healthy",
            "treatment": "Routine care",
            "follow_up_needed": False,
        }

        record = MedicalRecordSchema(**record_data)
        assert record.type == "checkup"
        assert record.description == "Annual wellness exam"
        assert record.date == "2023-06-10T14:30:00"
        assert record.veterinarian == "Dr. Johnson"
        assert record.diagnosis == "Healthy"
        assert record.treatment == "Routine care"
        assert record.follow_up_needed is False

    def test_required_fields(self):
        """Test that required fields are validated."""
        # Missing type
        with pytest.raises(ValidationError):
            MedicalRecordSchema(
                description="Test description", date="2023-06-10T14:30:00"
            )

        # Missing description
        with pytest.raises(ValidationError):
            MedicalRecordSchema(type="checkup", date="2023-06-10T14:30:00")

        # Missing date
        with pytest.raises(ValidationError):
            MedicalRecordSchema(type="checkup", description="Test description")

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        record = MedicalRecordSchema(
            type="checkup", description="Basic checkup", date="2023-06-10T14:30:00"
        )

        assert record.veterinarian is None
        assert record.diagnosis is None
        assert record.treatment is None
        assert record.follow_up_needed is False  # Default value


class TestAllergySchema:
    """Test AllergySchema validation."""

    def test_valid_allergy(self):
        """Test creating a valid allergy record."""
        allergy_data = {
            "allergen": "chicken",
            "reaction": "skin irritation",
            "severity": "moderate",
            "date_discovered": "2023-03-20T12:00:00",
        }

        allergy = AllergySchema(**allergy_data)
        assert allergy.allergen == "chicken"
        assert allergy.reaction == "skin irritation"
        assert allergy.severity == "moderate"
        assert allergy.date_discovered == "2023-03-20T12:00:00"

    def test_severity_validation(self):
        """Test severity level validation."""
        base_data = {"allergen": "chicken", "reaction": "skin irritation"}

        # Valid severities
        for severity in ["mild", "moderate", "severe", "unknown"]:
            allergy = AllergySchema(severity=severity, **base_data)
            assert allergy.severity == severity

        # Case insensitive
        allergy = AllergySchema(severity="MILD", **base_data)
        assert allergy.severity == "mild"

        # Invalid severity
        with pytest.raises(ValidationError):
            AllergySchema(severity="invalid", **base_data)

    def test_default_severity(self):
        """Test default severity value."""
        allergy = AllergySchema(allergen="chicken", reaction="skin irritation")
        assert allergy.severity == "unknown"


class TestEmergencyContactSchema:
    """Test EmergencyContactSchema validation."""

    def test_valid_emergency_contact(self):
        """Test creating a valid emergency contact."""
        contact_data = {
            "name": "Jane Doe",
            "phone": "+1 (555) 123-4567",
            "relationship": "spouse",
        }

        contact = EmergencyContactSchema(**contact_data)
        assert contact.name == "Jane Doe"
        assert contact.phone == "+1 (555) 123-4567"
        assert contact.relationship == "spouse"

    def test_required_fields(self):
        """Test that required fields are validated."""
        # Missing name
        with pytest.raises(ValidationError):
            EmergencyContactSchema(phone="+1 (555) 123-4567")

        # Missing phone
        with pytest.raises(ValidationError):
            EmergencyContactSchema(name="Jane Doe")

    def test_phone_validation(self):
        """Test phone number validation."""
        base_data = {"name": "Jane Doe"}

        # Valid phone numbers
        valid_phones = [
            "1234567890",
            "+1 (555) 123-4567",
            "555-123-4567",
            "+44 20 7946 0958",
        ]

        for phone in valid_phones:
            contact = EmergencyContactSchema(phone=phone, **base_data)
            assert contact.phone == phone

        # Invalid phone numbers
        with pytest.raises(ValidationError):
            EmergencyContactSchema(phone="123", **base_data)  # Too short

        with pytest.raises(ValidationError):
            EmergencyContactSchema(
                phone="12345678901234567890", **base_data
            )  # Too long


class TestPetBase:
    """Test PetBase schema validation."""

    def test_valid_pet_base(self):
        """Test creating a valid pet base."""
        pet_data = {
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "breed": "Golden Retriever",
            "gender": PetGender.MALE,
            "birth_date": date(2020, 5, 15),
            "weight_kg": Decimal("25.5"),
            "microchip_id": "123456789012345",
        }

        pet = PetBase(**pet_data)
        assert pet.name == "Buddy"
        assert pet.species == PetSpecies.DOG.value
        assert pet.breed == "Golden Retriever"
        assert pet.gender == PetGender.MALE.value
        assert pet.birth_date == date(2020, 5, 15)
        assert pet.weight_kg == Decimal("25.5")
        assert pet.microchip_id == "123456789012345"

    def test_name_validation(self):
        """Test pet name validation."""
        base_data = {"species": PetSpecies.DOG}

        # Valid names
        valid_names = ["Buddy", "Mr. Whiskers", "Bella-Rose", "Max Jr.", "D'Artagnan"]
        for name in valid_names:
            pet = PetBase(name=name, **base_data)
            assert pet.name == name

        # Invalid names
        with pytest.raises(ValidationError):
            PetBase(name="", **base_data)  # Empty name

        with pytest.raises(ValidationError):
            PetBase(name="Pet@Home", **base_data)  # Invalid characters

    def test_species_other_validation(self):
        """Test species 'other' validation."""
        # Species other without description should fail
        with pytest.raises(ValidationError):
            PetBase(name="Spike", species=PetSpecies.OTHER)

        # Species other with description should pass
        pet = PetBase(
            name="Spike",
            species=PetSpecies.OTHER,
            species_other_description="bearded dragon",
        )
        assert pet.species == PetSpecies.OTHER.value
        assert pet.species_other_description == "bearded dragon"

        # Non-other species with description should pass (description ignored)
        pet = PetBase(
            name="Buddy", species=PetSpecies.DOG, species_other_description="ignored"
        )
        assert pet.species == PetSpecies.DOG.value
        assert pet.species_other_description == "ignored"

    def test_birth_date_validation(self):
        """Test birth date validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # Valid birth date (past)
        past_date = date(2020, 1, 1)
        pet = PetBase(birth_date=past_date, **base_data)
        assert pet.birth_date == past_date

        # Today should be valid
        today = date.today()
        pet = PetBase(birth_date=today, **base_data)
        assert pet.birth_date == today

        # Future date should be invalid
        from datetime import timedelta

        future_date = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError):
            PetBase(birth_date=future_date, **base_data)

    def test_weight_validation(self):
        """Test weight validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # Valid weights
        pet = PetBase(weight_kg=Decimal("25.5"), **base_data)
        assert pet.weight_kg == Decimal("25.5")

        # Zero weight should be invalid
        with pytest.raises(ValidationError):
            PetBase(weight_kg=Decimal("0"), **base_data)

        # Negative weight should be invalid
        with pytest.raises(ValidationError):
            PetBase(weight_kg=Decimal("-5.0"), **base_data)

        # Extremely high weight should be invalid
        with pytest.raises(ValidationError):
            PetBase(weight_kg=Decimal("1000.0"), **base_data)

    def test_microchip_validation(self):
        """Test microchip ID validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # Valid microchip IDs
        valid_chips = ["123456789012345", "ABCDEF123456789", "1A2B3C4D5E6F7G8"]
        for chip_id in valid_chips:
            pet = PetBase(microchip_id=chip_id, **base_data)
            assert pet.microchip_id == chip_id

        # Invalid microchip IDs
        with pytest.raises(ValidationError):
            PetBase(microchip_id="1234567", **base_data)  # Too short

        with pytest.raises(ValidationError):
            PetBase(microchip_id="123456789012345678901", **base_data)  # Too long

        with pytest.raises(ValidationError):
            PetBase(microchip_id="123-456-789", **base_data)  # Invalid characters

    def test_microchip_consistency_validation(self):
        """Test microchip consistency validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # is_microchipped=True but no microchip_id should fail
        with pytest.raises(ValidationError):
            PetBase(is_microchipped=True, **base_data)

        # is_microchipped=True with microchip_id should pass
        pet = PetBase(is_microchipped=True, microchip_id="123456789012345", **base_data)
        assert pet.is_microchipped is True
        assert pet.microchip_id == "123456789012345"

        # is_microchipped=False with microchip_id should pass (microchip exists but not active)
        pet = PetBase(
            is_microchipped=False, microchip_id="123456789012345", **base_data
        )
        assert pet.is_microchipped is False
        assert pet.microchip_id == "123456789012345"

    def test_insurance_consistency_validation(self):
        """Test insurance consistency validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # is_insured=True but no insurance_provider should fail
        with pytest.raises(ValidationError):
            PetBase(is_insured=True, **base_data)

        # is_insured=True with insurance_provider should pass
        pet = PetBase(
            is_insured=True, insurance_provider="Pet Insurance Co", **base_data
        )
        assert pet.is_insured is True
        assert pet.insurance_provider == "Pet Insurance Co"

    def test_age_consistency_validation(self):
        """Test age information consistency validation."""
        base_data = {"name": "Buddy", "species": PetSpecies.DOG}

        # Both birth_date and approximate age should fail
        with pytest.raises(ValidationError):
            PetBase(birth_date=date(2020, 1, 1), approximate_age_years=3, **base_data)

        # Only birth_date should pass
        pet = PetBase(birth_date=date(2020, 1, 1), **base_data)
        assert pet.birth_date == date(2020, 1, 1)
        assert pet.approximate_age_years is None

        # Only approximate age should pass
        pet = PetBase(approximate_age_years=3, approximate_age_months=6, **base_data)
        assert pet.birth_date is None
        assert pet.approximate_age_years == 3
        assert pet.approximate_age_months == 6


class TestPetCreate:
    """Test PetCreate schema validation."""

    def test_valid_pet_create(self):
        """Test creating a valid pet."""
        owner_id = uuid4()
        pet_data = {
            "owner_id": owner_id,
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "breed": "Golden Retriever",
            "gender": PetGender.MALE,
            "birth_date": date(2020, 5, 15),
            "weight_kg": Decimal("25.5"),
            "status": PetStatus.ACTIVE,
        }

        pet = PetCreate(**pet_data)
        assert pet.owner_id == owner_id
        assert pet.name == "Buddy"
        assert pet.species == PetSpecies.DOG.value
        assert pet.status == PetStatus.ACTIVE.value

    def test_with_vaccination_records(self):
        """Test creating pet with vaccination records."""
        owner_id = uuid4()
        vaccination_records = [
            {
                "vaccine_type": "rabies",
                "date": "2023-01-15T10:00:00",
                "veterinarian": "Dr. Smith",
            }
        ]

        pet_data = {
            "owner_id": owner_id,
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "vaccination_records": vaccination_records,
        }

        pet = PetCreate(**pet_data)
        assert len(pet.vaccination_records) == 1
        assert pet.vaccination_records[0].vaccine_type == "Rabies"

    def test_with_allergy_information(self):
        """Test creating pet with allergy information."""
        owner_id = uuid4()
        allergies = [
            {
                "allergen": "chicken",
                "reaction": "skin irritation",
                "severity": "moderate",
            }
        ]

        pet_data = {
            "owner_id": owner_id,
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "allergy_information": allergies,
        }

        pet = PetCreate(**pet_data)
        assert len(pet.allergy_information) == 1
        assert pet.allergy_information[0].allergen == "chicken"

    def test_vaccination_records_limit(self):
        """Test vaccination records limit."""
        owner_id = uuid4()

        # Create too many vaccination records
        vaccination_records = []
        for i in range(51):  # Exceeds limit of 50
            vaccination_records.append(
                {
                    "vaccine_type": f"vaccine_{i}",
                    "date": "2023-01-15T10:00:00",
                    "veterinarian": "Dr. Smith",
                }
            )

        pet_data = {
            "owner_id": owner_id,
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "vaccination_records": vaccination_records,
        }

        with pytest.raises(ValidationError):
            PetCreate(**pet_data)

    def test_allergy_information_limit(self):
        """Test allergy information limit."""
        owner_id = uuid4()

        # Create too many allergy records
        allergies = []
        for i in range(21):  # Exceeds limit of 20
            allergies.append(
                {
                    "allergen": f"allergen_{i}",
                    "reaction": "reaction",
                    "severity": "mild",
                }
            )

        pet_data = {
            "owner_id": owner_id,
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "allergy_information": allergies,
        }

        with pytest.raises(ValidationError):
            PetCreate(**pet_data)


class TestPetUpdate:
    """Test PetUpdate schema validation."""

    def test_valid_pet_update(self):
        """Test valid pet update."""
        update_data = {
            "name": "Buddy Updated",
            "weight_kg": Decimal("26.0"),
            "temperament": "Friendly and energetic",
        }

        pet_update = PetUpdate(**update_data)
        assert pet_update.name == "Buddy Updated"
        assert pet_update.weight_kg == Decimal("26.0")
        assert pet_update.temperament == "Friendly and energetic"

    def test_partial_update(self):
        """Test partial pet update."""
        # Only update name
        pet_update = PetUpdate(name="New Name")
        assert pet_update.name == "New Name"
        assert pet_update.weight_kg is None

        # Only update status
        pet_update = PetUpdate(status=PetStatus.INACTIVE)
        assert pet_update.status == PetStatus.INACTIVE.value

    def test_empty_update_validation(self):
        """Test that empty update is rejected."""
        with pytest.raises(ValidationError):
            PetUpdate()

    def test_update_field_validation(self):
        """Test that update fields use same validation as create."""
        # Invalid weight
        with pytest.raises(ValidationError):
            PetUpdate(weight_kg=Decimal("0"))

        # Invalid name
        with pytest.raises(ValidationError):
            PetUpdate(name="")


class TestPetResponse:
    """Test PetResponse schema."""

    def test_pet_response_creation(self):
        """Test creating pet response from model data."""
        pet_data = {
            "id": uuid4(),
            "owner_id": uuid4(),
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "breed": "Golden Retriever",
            "mixed_breed": False,
            "gender": PetGender.MALE,
            "status": PetStatus.ACTIVE,
            "is_spayed_neutered": True,
            "is_microchipped": True,
            "is_insured": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        response = PetResponse(**pet_data)
        assert response.id == pet_data["id"]
        assert response.owner_id == pet_data["owner_id"]
        assert response.name == "Buddy"
        assert response.species == PetSpecies.DOG.value
        assert response.status == PetStatus.ACTIVE.value


class TestPetMedicalHistoryUpdate:
    """Test PetMedicalHistoryUpdate schema."""

    def test_valid_medical_history_update(self):
        """Test valid medical history update."""
        medical_records = [
            {
                "type": "checkup",
                "description": "Annual wellness exam",
                "date": "2023-06-10T14:30:00",
            }
        ]

        update = PetMedicalHistoryUpdate(medical_records=medical_records)
        assert len(update.medical_records) == 1
        assert update.medical_records[0].type == "checkup"

    def test_empty_medical_records(self):
        """Test that empty medical records are rejected."""
        with pytest.raises(ValidationError):
            PetMedicalHistoryUpdate(medical_records=[])

    def test_too_many_medical_records(self):
        """Test medical records limit."""
        medical_records = []
        for i in range(11):  # Exceeds limit of 10
            medical_records.append(
                {
                    "type": "checkup",
                    "description": f"Checkup {i}",
                    "date": "2023-06-10T14:30:00",
                }
            )

        with pytest.raises(ValidationError):
            PetMedicalHistoryUpdate(medical_records=medical_records)


class TestPetVaccinationUpdate:
    """Test PetVaccinationUpdate schema."""

    def test_valid_vaccination_update(self):
        """Test valid vaccination update."""
        vaccination_records = [
            {
                "vaccine_type": "rabies",
                "date": "2023-01-15T10:00:00",
                "veterinarian": "Dr. Smith",
            }
        ]

        update = PetVaccinationUpdate(vaccination_records=vaccination_records)
        assert len(update.vaccination_records) == 1
        assert update.vaccination_records[0].vaccine_type == "Rabies"

    def test_empty_vaccination_records(self):
        """Test that empty vaccination records are rejected."""
        with pytest.raises(ValidationError):
            PetVaccinationUpdate(vaccination_records=[])

    def test_too_many_vaccination_records(self):
        """Test vaccination records limit."""
        vaccination_records = []
        for i in range(6):  # Exceeds limit of 5
            vaccination_records.append(
                {
                    "vaccine_type": f"vaccine_{i}",
                    "date": "2023-01-15T10:00:00",
                    "veterinarian": "Dr. Smith",
                }
            )

        with pytest.raises(ValidationError):
            PetVaccinationUpdate(vaccination_records=vaccination_records)


class TestPetWeightUpdate:
    """Test PetWeightUpdate schema."""

    def test_valid_weight_update(self):
        """Test valid weight update."""
        update = PetWeightUpdate(weight_kg=Decimal("25.5"), recorded_by="Dr. Smith")
        assert update.weight_kg == Decimal("25.5")
        assert update.recorded_by == "Dr. Smith"

    def test_weight_validation(self):
        """Test weight validation."""
        # Valid weight
        update = PetWeightUpdate(weight_kg=Decimal("25.5"))
        assert update.weight_kg == Decimal("25.5")

        # Invalid weights
        with pytest.raises(ValidationError):
            PetWeightUpdate(weight_kg=Decimal("0"))

        with pytest.raises(ValidationError):
            PetWeightUpdate(weight_kg=Decimal("-5.0"))

        with pytest.raises(ValidationError):
            PetWeightUpdate(weight_kg=Decimal("1000.0"))

    def test_optional_recorded_by(self):
        """Test optional recorded_by field."""
        update = PetWeightUpdate(weight_kg=Decimal("25.5"))
        assert update.recorded_by is None

        # Empty string should be converted to None
        update = PetWeightUpdate(weight_kg=Decimal("25.5"), recorded_by="")
        assert update.recorded_by is None

        # Whitespace should be converted to None
        update = PetWeightUpdate(weight_kg=Decimal("25.5"), recorded_by="   ")
        assert update.recorded_by is None


class TestPetListResponse:
    """Test PetListResponse schema."""

    def test_pet_list_response_creation(self):
        """Test creating pet list response."""
        pet_data = {
            "id": uuid4(),
            "owner_id": uuid4(),
            "name": "Buddy",
            "species": PetSpecies.DOG,
            "breed": "Golden Retriever",
            "gender": PetGender.MALE,
            "status": PetStatus.ACTIVE,
            "profile_photo_url": "https://example.com/photo.jpg",
            "created_at": datetime.now(),
        }

        response = PetListResponse(**pet_data)
        assert response.id == pet_data["id"]
        assert response.name == "Buddy"
        assert response.species == PetSpecies.DOG.value
        assert response.profile_photo_url == "https://example.com/photo.jpg"
