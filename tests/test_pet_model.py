"""
Tests for the Pet model.

This module contains comprehensive tests for the Pet SQLAlchemy model,
including validation, relationships, business logic, and edge cases.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from vet_core.models import (
    Base,
    Pet,
    PetGender,
    PetSize,
    PetSpecies,
    PetStatus,
    User,
    UserRole,
)


@pytest.fixture
def sample_pet_data():
    """Sample pet data for testing."""
    return {
        "name": "Buddy",
        "species": PetSpecies.DOG,
        "breed": "Golden Retriever",
        "gender": PetGender.MALE,
        "birth_date": date(2020, 5, 15),
        "weight_kg": Decimal("29.7"),  # ~65.5 lbs
        "microchip_id": "123456789012345",
    }


class TestPetModel:
    """Test cases for the Pet model."""

    def test_pet_creation_with_required_fields(self):
        """Test creating a pet with only required fields."""
        owner_id = uuid.uuid4()
        pet = Pet(owner_id=owner_id, name="Buddy", species=PetSpecies.DOG)

        assert pet.owner_id == owner_id
        assert pet.name == "Buddy"
        assert pet.species == PetSpecies.DOG
        assert pet.status == PetStatus.ACTIVE  # Default value
        assert pet.gender == PetGender.UNKNOWN  # Default value
        assert not pet.is_spayed_neutered  # Default value
        assert not pet.is_microchipped  # Default value
        assert not pet.is_insured  # Default value

    @pytest_asyncio.fixture
    async def test_pet_database_creation(
        self, async_session, user_factory, pet_factory
    ):
        """Test pet creation and persistence in database."""
        user = await user_factory.create(async_session)

        pet_data = {
            "name": "Database Pet",
            "species": PetSpecies.CAT,
            "breed": "Persian",
            "gender": PetGender.FEMALE,
            "weight_kg": Decimal("4.5"),
            "is_microchipped": True,
            "microchip_id": "test_chip_123",
        }

        pet = await pet_factory.create(async_session, owner=user, **pet_data)

        assert pet.id is not None
        assert pet.created_at is not None
        assert pet.updated_at is not None
        assert pet.owner_id == user.id
        assert pet.name == "Database Pet"
        assert pet.species == PetSpecies.CAT
        assert pet.breed == "Persian"
        assert pet.is_active

        return pet

    def test_pet_creation_with_all_fields(self, session, sample_user, sample_pet_data):
        """Test creating a pet with all fields populated."""
        pet_data = sample_pet_data.copy()
        pet_data["owner_id"] = sample_user.id
        pet_data["mixed_breed"] = False
        pet_data["is_spayed_neutered"] = True
        pet_data["spay_neuter_date"] = date(2021, 3, 10)
        pet_data["is_microchipped"] = True
        pet_data["microchip_date"] = date(2020, 6, 1)
        pet_data["temperament"] = "Friendly and energetic"
        pet_data["special_needs"] = "Needs daily medication"

        pet = Pet(**pet_data)
        session.add(pet)
        session.commit()

        assert pet.name == "Buddy"
        assert pet.species == PetSpecies.DOG
        assert pet.breed == "Golden Retriever"
        assert pet.gender == PetGender.MALE
        assert pet.birth_date == date(2020, 5, 15)
        assert pet.weight_kg == Decimal("29.7")
        assert pet.microchip_id == "123456789012345"
        assert pet.is_spayed_neutered
        assert pet.spay_neuter_date == date(2021, 3, 10)
        assert pet.is_microchipped
        assert pet.microchip_date == date(2020, 6, 1)
        assert pet.temperament == "Friendly and energetic"
        assert pet.special_needs == "Needs daily medication"

    def test_pet_age_calculation_with_birth_date(self, session, sample_user):
        """Test age calculation when birth date is provided."""
        # Pet born 2 years ago
        birth_date = date.today() - timedelta(days=730)  # Approximately 2 years
        pet = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            birth_date=birth_date,
        )

        session.add(pet)
        session.commit()

        age = pet.age_in_years
        assert age == 2 or age == 1  # Account for leap years and exact dates
        assert "year" in pet.age_display

    def test_pet_age_calculation_with_approximate_age(self, session, sample_user):
        """Test age calculation when approximate age is provided."""
        pet = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            approximate_age_years=3,
            approximate_age_months=6,
        )

        session.add(pet)
        session.commit()

        assert pet.age_in_years == 3
        assert "3 year" in pet.age_display
        assert "6 month" in pet.age_display

    def test_pet_young_age_display(self, session, sample_user):
        """Test age display for very young pets (less than 1 year)."""
        # Pet born 6 months ago
        birth_date = date.today() - timedelta(days=180)
        pet = Pet(
            owner_id=sample_user.id,
            name="Puppy",
            species=PetSpecies.DOG,
            birth_date=birth_date,
        )

        session.add(pet)
        session.commit()

        age_display = pet.age_display
        assert "month" in age_display
        assert "year" not in age_display or "0 year" in age_display

    def test_pet_weight_display(self, session, sample_user):
        """Test weight display formatting."""
        pet = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            weight_kg=Decimal("20.8"),  # ~45.75 lbs
        )

        session.add(pet)
        session.commit()

        assert pet.weight_display == "20.8 kg"

        # Test pet without weight
        pet_no_weight = Pet(
            owner_id=sample_user.id, name="Unknown Weight", species=PetSpecies.CAT
        )

        session.add(pet_no_weight)
        session.commit()

        assert pet_no_weight.weight_display == "Unknown"

    def test_pet_breed_display(self, session, sample_user):
        """Test breed display formatting."""
        # Regular breed
        pet1 = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            breed="Golden Retriever",
            mixed_breed=False,
        )
        assert pet1.breed_display == "Golden Retriever"

        # Mixed breed with known primary breed
        pet2 = Pet(
            owner_id=sample_user.id,
            name="Max",
            species=PetSpecies.DOG,
            breed="Labrador",
            mixed_breed=True,
        )
        assert pet2.breed_display == "Labrador Mix"

        # Mixed breed without specific breed
        pet3 = Pet(
            owner_id=sample_user.id,
            name="Rex",
            species=PetSpecies.DOG,
            mixed_breed=True,
        )
        assert pet3.breed_display == "Mixed Breed"

        # Unknown breed
        pet4 = Pet(owner_id=sample_user.id, name="Mystery", species=PetSpecies.CAT)
        assert pet4.breed_display == "Unknown"

    def test_pet_vaccination_tracking(self, session, sample_user):
        """Test vaccination record management."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        # Add vaccination record
        vaccination_date = date(2023, 1, 15)
        pet.add_vaccination_record(
            vaccine_type="Rabies",
            date_administered=vaccination_date,
            veterinarian="Dr. Smith",
            batch_number="RB123456",
            next_due_date=date(2024, 1, 15),
            notes="No adverse reactions",
        )

        session.commit()

        # Check vaccination was added
        assert pet.vaccination_records is not None
        assert len(pet.vaccination_records) == 1

        record = pet.vaccination_records[0]
        assert record["vaccine_type"] == "Rabies"
        assert record["date"] == vaccination_date.isoformat()
        assert record["veterinarian"] == "Dr. Smith"
        assert record["batch_number"] == "RB123456"
        assert record["notes"] == "No adverse reactions"

        # Test getting latest vaccination
        latest = pet.get_latest_vaccination("Rabies")
        assert latest is not None
        assert latest["vaccine_type"] == "Rabies"

        # Test vaccination due check
        assert not pet.is_due_for_vaccination("Rabies")  # Recently vaccinated

    def test_pet_medical_history_tracking(self, session, sample_user):
        """Test medical record management."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        # Add medical record
        record_date = date(2023, 6, 10)
        pet.add_medical_record(
            record_type="checkup",
            description="Annual wellness exam",
            date_recorded=record_date,
            veterinarian="Dr. Johnson",
            diagnosis="Healthy",
            treatment="Routine care",
            follow_up_needed=False,
        )

        session.commit()

        # Check medical record was added
        assert pet.medical_history is not None
        assert "records" in pet.medical_history
        assert len(pet.medical_history["records"]) == 1

        record = pet.medical_history["records"][0]
        assert record["type"] == "checkup"
        assert record["description"] == "Annual wellness exam"
        assert record["date"] == record_date.isoformat()
        assert record["veterinarian"] == "Dr. Johnson"
        assert record["diagnosis"] == "Healthy"
        assert record["treatment"] == "Routine care"
        assert not record["follow_up_needed"]

        # Test getting records by type
        checkup_records = pet.get_medical_records_by_type("checkup")
        assert len(checkup_records) == 1
        assert checkup_records[0]["type"] == "checkup"

    def test_pet_allergy_management(self, session, sample_user):
        """Test allergy information management."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        # Add allergy
        discovery_date = date(2023, 3, 20)
        pet.add_allergy(
            allergen="Chicken",
            reaction="Skin irritation and itching",
            severity="moderate",
            date_discovered=discovery_date,
        )

        session.commit()

        # Check allergy was added
        assert pet.allergy_information is not None
        assert len(pet.allergy_information) == 1

        allergy = pet.allergy_information[0]
        assert allergy["allergen"] == "Chicken"
        assert allergy["reaction"] == "Skin irritation and itching"
        assert allergy["severity"] == "moderate"
        assert allergy["date_discovered"] == discovery_date.isoformat()

    def test_pet_weight_update_with_history(self, session, sample_user):
        """Test weight updates with history tracking."""
        pet = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            weight_kg=Decimal("22.7"),  # ~50 lbs
            medical_history={},
        )

        session.add(pet)
        session.commit()

        # Update weight
        new_weight = Decimal("25.2")  # ~55.5 lbs
        pet.update_weight(new_weight, recorded_by="Dr. Smith")

        session.commit()

        # Check weight was updated
        assert pet.weight_kg == new_weight

        # Check weight history was recorded
        assert "weight_history" in pet.medical_history
        assert len(pet.medical_history["weight_history"]) == 1

        history_record = pet.medical_history["weight_history"][0]
        assert history_record["weight_kg"] == 22.7  # Previous weight
        assert history_record["recorded_by"] == "Dr. Smith"

        # Check size category was updated (for dogs)
        assert pet.size_category == PetSize.MEDIUM  # 25.2 kg should be medium

    def test_pet_size_category_assignment(self, session, sample_user):
        """Test automatic size category assignment based on weight."""
        test_cases = [
            (Decimal("1.4"), PetSize.EXTRA_SMALL),  # ~3 lbs
            (Decimal("6.8"), PetSize.SMALL),  # ~15 lbs
            (Decimal("20.4"), PetSize.MEDIUM),  # ~45 lbs
            (Decimal("36.3"), PetSize.LARGE),  # ~80 lbs
            (Decimal("54.4"), PetSize.EXTRA_LARGE),  # ~120 lbs
        ]

        for weight, expected_size in test_cases:
            pet = Pet(
                owner_id=sample_user.id, name=f"Dog_{weight}", species=PetSpecies.DOG
            )
            pet.update_weight(weight)

            assert (
                pet.size_category == expected_size
            ), f"Weight {weight} kg should be {expected_size}"

    def test_pet_deceased_marking(self, session, sample_user):
        """Test marking a pet as deceased."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        # Mark as deceased
        death_date = date(2023, 12, 1)
        pet.mark_deceased(date_of_death=death_date, cause="Old age")

        session.commit()

        # Check status was updated
        assert pet.status == PetStatus.DECEASED
        assert not pet.is_active

        # Check deceased information was recorded
        assert "deceased" in pet.medical_history
        deceased_info = pet.medical_history["deceased"]
        assert deceased_info["date_of_death"] == death_date.isoformat()
        assert deceased_info["cause"] == "Old age"

    def test_pet_ownership_transfer(self, session, sample_user):
        """Test transferring pet ownership."""
        # Create second user
        new_owner = User(
            clerk_user_id="new_owner_123",
            email="newowner@example.com",
            first_name="Jane",
            last_name="Smith",
            role=UserRole.PET_OWNER,
        )
        session.add(new_owner)
        session.commit()

        # Create pet
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        original_owner_id = pet.owner_id

        # Transfer ownership
        pet.transfer_ownership(new_owner.id, transfer_reason="Moving abroad")

        session.commit()

        # Check ownership was transferred
        assert pet.owner_id == new_owner.id

        # Check transfer history was recorded
        assert "ownership_history" in pet.medical_history
        assert len(pet.medical_history["ownership_history"]) == 1

        transfer_record = pet.medical_history["ownership_history"][0]
        assert transfer_record["previous_owner_id"] == str(original_owner_id)
        assert transfer_record["new_owner_id"] == str(new_owner.id)
        assert transfer_record["reason"] == "Moving abroad"

    def test_pet_active_status_check(self, session, sample_user):
        """Test active status checking."""
        pet = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            status=PetStatus.ACTIVE,
        )

        session.add(pet)
        session.commit()

        # Pet should be active
        assert pet.is_active

        # Mark as inactive
        pet.status = PetStatus.INACTIVE
        assert not pet.is_active

        # Soft delete
        pet.status = PetStatus.ACTIVE
        pet.soft_delete()
        assert not pet.is_active

    def test_pet_string_representation(self, session, sample_user):
        """Test string representation of Pet model."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        repr_str = repr(pet)
        assert "Pet(" in repr_str
        assert f"id={pet.id}" in repr_str
        assert "name='Buddy'" in repr_str
        assert "species='dog'" in repr_str
        assert f"owner_id={sample_user.id}" in repr_str

    def test_pet_display_name(self, session, sample_user):
        """Test display name property."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        assert pet.display_name == "Buddy"

    def test_pet_microchip_uniqueness(self, session, sample_user):
        """Test that microchip IDs are unique."""
        microchip_id = "123456789012345"

        # Create first pet with microchip
        pet1 = Pet(
            owner_id=sample_user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            microchip_id=microchip_id,
        )

        session.add(pet1)
        session.commit()

        # Try to create second pet with same microchip ID
        pet2 = Pet(
            owner_id=sample_user.id,
            name="Max",
            species=PetSpecies.CAT,
            microchip_id=microchip_id,
        )

        session.add(pet2)

        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # SQLAlchemy will raise an IntegrityError
            session.commit()

    def test_pet_jsonb_fields_initialization(self, session, sample_user):
        """Test that JSONB fields are properly initialized."""
        pet = Pet(owner_id=sample_user.id, name="Buddy", species=PetSpecies.DOG)

        session.add(pet)
        session.commit()

        # JSONB fields should be None initially
        assert pet.medical_history is None
        assert pet.vaccination_records is None
        assert pet.medication_history is None
        assert pet.allergy_information is None
        assert pet.emergency_contact is None
        assert pet.additional_photos is None

    def test_pet_enum_values(self):
        """Test that enum values are correct."""
        # Test PetSpecies enum
        assert PetSpecies.DOG.value == "dog"
        assert PetSpecies.CAT.value == "cat"
        assert PetSpecies.BIRD.value == "bird"

        # Test PetGender enum
        assert PetGender.MALE.value == "male"
        assert PetGender.FEMALE.value == "female"
        assert PetGender.UNKNOWN.value == "unknown"

        # Test PetSize enum
        assert PetSize.EXTRA_SMALL.value == "extra_small"
        assert PetSize.SMALL.value == "small"
        assert PetSize.MEDIUM.value == "medium"
        assert PetSize.LARGE.value == "large"
        assert PetSize.EXTRA_LARGE.value == "extra_large"

        # Test PetStatus enum
        assert PetStatus.ACTIVE.value == "active"
        assert PetStatus.INACTIVE.value == "inactive"
        assert PetStatus.DECEASED.value == "deceased"
        assert PetStatus.LOST.value == "lost"
        assert PetStatus.TRANSFERRED.value == "transferred"
