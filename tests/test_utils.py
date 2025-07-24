"""
Test utilities for the vet-core package.

This module provides utility functions and classes for testing,
including database cleanup, test data generation, and assertion helpers.
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vet_core.models import (
    Appointment,
    AppointmentStatus,
    Clinic,
    Pet,
    PetSpecies,
    User,
    UserRole,
    Veterinarian,
)
from vet_core.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)


class DatabaseTestUtils:
    """Utilities for database testing operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_records(self, model_class: Type[T], **filters) -> int:
        """Count records in a table with optional filters."""
        query = select(model_class)

        for field, value in filters.items():
            if hasattr(model_class, field):
                query = query.where(getattr(model_class, field) == value)

        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def get_all_records(self, model_class: Type[T], **filters) -> List[T]:
        """Get all records from a table with optional filters."""
        query = select(model_class)

        for field, value in filters.items():
            if hasattr(model_class, field):
                query = query.where(getattr(model_class, field) == value)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_all_records(self, model_class: Type[T]) -> int:
        """Delete all records from a table and return count deleted."""
        result = await self.session.execute(delete(model_class))
        return result.rowcount

    async def record_exists(self, model_class: Type[T], record_id: uuid.UUID) -> bool:
        """Check if a record exists by ID."""
        query = select(model_class).where(model_class.id == record_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_record_by_id(
        self, model_class: Type[T], record_id: uuid.UUID
    ) -> Optional[T]:
        """Get a record by ID."""
        query = select(model_class).where(model_class.id == record_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def refresh_record(self, record: BaseModel) -> None:
        """Refresh a record from the database."""
        await self.session.refresh(record)

    async def flush_and_refresh(self, record: BaseModel) -> None:
        """Flush changes and refresh a record."""
        await self.session.flush()
        await self.session.refresh(record)


class TestDataBuilder:
    """Builder class for creating complex test data scenarios."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.created_records = []

    async def create_user_with_pets(
        self,
        user_data: Optional[Dict[str, Any]] = None,
        pet_count: int = 2,
        pet_data_list: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[User, List[Pet]]:
        """Create a user with multiple pets."""
        from .conftest import PetFactory, UserFactory

        # Create user
        user = await UserFactory.create(self.session, **(user_data or {}))
        self.created_records.append(user)

        # Create pets
        pets = []
        for i in range(pet_count):
            pet_data = (
                pet_data_list[i] if pet_data_list and i < len(pet_data_list) else {}
            )
            pet = await PetFactory.create(self.session, owner=user, **pet_data)
            pets.append(pet)
            self.created_records.append(pet)

        return user, pets

    async def create_clinic_with_veterinarians(
        self,
        clinic_data: Optional[Dict[str, Any]] = None,
        vet_count: int = 2,
        vet_data_list: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[Clinic, List[Veterinarian]]:
        """Create a clinic with multiple veterinarians."""
        from .conftest import ClinicFactory, UserFactory, VeterinarianFactory

        # Create clinic
        clinic = await ClinicFactory.create(self.session, **(clinic_data or {}))
        self.created_records.append(clinic)

        # Create veterinarians
        veterinarians = []
        for i in range(vet_count):
            vet_data = (
                vet_data_list[i] if vet_data_list and i < len(vet_data_list) else {}
            )

            # Create user for veterinarian
            user = await UserFactory.create_veterinarian(self.session)
            self.created_records.append(user)

            # Create veterinarian
            vet = await VeterinarianFactory.create(
                self.session, user=user, clinic=clinic, **vet_data
            )
            veterinarians.append(vet)
            self.created_records.append(vet)

        return clinic, veterinarians

    async def create_appointment_scenario(
        self,
        appointment_count: int = 3,
        include_past: bool = True,
        include_future: bool = True,
    ) -> Dict[str, Any]:
        """Create a complete appointment scenario with all related entities."""
        from .conftest import AppointmentFactory

        # Create base entities
        user, pets = await self.create_user_with_pets(pet_count=2)
        clinic, veterinarians = await self.create_clinic_with_veterinarians(vet_count=2)

        # Create appointments
        appointments = []
        base_date = datetime.now()

        for i in range(appointment_count):
            # Vary appointment times
            if include_past and i % 3 == 0:
                scheduled_at = base_date - timedelta(days=7 + i)
                status = AppointmentStatus.COMPLETED
            elif include_future and i % 3 == 1:
                scheduled_at = base_date + timedelta(days=7 + i)
                status = AppointmentStatus.SCHEDULED
            else:
                scheduled_at = base_date + timedelta(hours=i)
                status = AppointmentStatus.CONFIRMED

            appointment = await AppointmentFactory.create(
                self.session,
                pet=pets[i % len(pets)],
                veterinarian=veterinarians[i % len(veterinarians)],
                clinic=clinic,
                scheduled_at=scheduled_at,
                status=status,
            )
            appointments.append(appointment)
            self.created_records.append(appointment)

        return {
            "user": user,
            "pets": pets,
            "clinic": clinic,
            "veterinarians": veterinarians,
            "appointments": appointments,
        }

    async def cleanup(self):
        """Clean up all created records."""
        # Delete in reverse order to handle foreign key constraints
        for record in reversed(self.created_records):
            try:
                await self.session.delete(record)
            except Exception:
                # Record might already be deleted
                pass

        self.created_records.clear()


class AssertionHelpers:
    """Helper functions for common test assertions."""

    @staticmethod
    def assert_user_fields(user: User, expected_data: Dict[str, Any]):
        """Assert that user fields match expected data."""
        for field, expected_value in expected_data.items():
            actual_value = getattr(user, field)
            assert (
                actual_value == expected_value
            ), f"User.{field}: expected {expected_value}, got {actual_value}"

    @staticmethod
    def assert_pet_fields(pet: Pet, expected_data: Dict[str, Any]):
        """Assert that pet fields match expected data."""
        for field, expected_value in expected_data.items():
            actual_value = getattr(pet, field)
            assert (
                actual_value == expected_value
            ), f"Pet.{field}: expected {expected_value}, got {actual_value}"

    @staticmethod
    def assert_appointment_fields(
        appointment: Appointment, expected_data: Dict[str, Any]
    ):
        """Assert that appointment fields match expected data."""
        for field, expected_value in expected_data.items():
            actual_value = getattr(appointment, field)
            assert (
                actual_value == expected_value
            ), f"Appointment.{field}: expected {expected_value}, got {actual_value}"

    @staticmethod
    def assert_record_count(
        actual_count: int, expected_count: int, entity_name: str = "records"
    ):
        """Assert record count with descriptive message."""
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} {entity_name}, got {actual_count}"

    @staticmethod
    def assert_record_exists(record: Optional[BaseModel], entity_name: str = "record"):
        """Assert that a record exists (is not None)."""
        assert record is not None, f"Expected {entity_name} to exist, but got None"

    @staticmethod
    def assert_record_not_exists(
        record: Optional[BaseModel], entity_name: str = "record"
    ):
        """Assert that a record does not exist (is None)."""
        assert record is None, f"Expected {entity_name} to not exist, but got {record}"

    @staticmethod
    def assert_datetime_close(
        actual: datetime, expected: datetime, tolerance_seconds: int = 5
    ):
        """Assert that two datetimes are close within tolerance."""
        diff = abs((actual - expected).total_seconds())
        assert (
            diff <= tolerance_seconds
        ), f"Datetime difference {diff}s exceeds tolerance {tolerance_seconds}s"

    @staticmethod
    def assert_decimal_close(
        actual: Decimal, expected: Decimal, tolerance: Decimal = Decimal("0.01")
    ):
        """Assert that two decimal values are close within tolerance."""
        diff = abs(actual - expected)
        assert (
            diff <= tolerance
        ), f"Decimal difference {diff} exceeds tolerance {tolerance}"


class MockDataScenarios:
    """Pre-defined test data scenarios for common testing patterns."""

    @staticmethod
    def get_user_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get various user test scenarios."""
        return {
            "pet_owner": {
                "role": UserRole.PET_OWNER,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
            },
            "veterinarian": {
                "role": UserRole.VETERINARIAN,
                "first_name": "Dr. Jane",
                "last_name": "Smith",
                "email": "jane.smith@vetclinic.com",
                "phone_number": "+1987654321",
            },
            "admin": {
                "role": UserRole.PLATFORM_ADMIN,
                "first_name": "Admin",
                "last_name": "User",
                "email": "admin@platform.com",
            },
            "incomplete_profile": {
                "role": UserRole.PET_OWNER,
                "first_name": "Incomplete",
                "last_name": "User",
                "email": "incomplete@example.com",
                "phone_number": None,  # Missing required field
                "address_line1": None,
            },
        }

    @staticmethod
    def get_pet_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get various pet test scenarios."""
        return {
            "healthy_dog": {
                "name": "Buddy",
                "species": PetSpecies.DOG,
                "breed": "Golden Retriever",
                "birth_date": date(2020, 5, 15),
                "weight_kg": Decimal("30.5"),
                "is_spayed_neutered": True,
                "is_microchipped": True,
            },
            "young_cat": {
                "name": "Whiskers",
                "species": PetSpecies.CAT,
                "breed": "Domestic Shorthair",
                "birth_date": date(2023, 1, 10),
                "weight_kg": Decimal("3.2"),
                "is_spayed_neutered": False,
                "is_microchipped": False,
            },
            "exotic_pet": {
                "name": "Spike",
                "species": PetSpecies.OTHER,
                "species_other_description": "bearded dragon",
                "birth_date": date(2021, 8, 20),
                "weight_kg": Decimal("0.5"),
                "is_spayed_neutered": False,
                "is_microchipped": False,
            },
            "senior_pet": {
                "name": "Old Timer",
                "species": PetSpecies.DOG,
                "breed": "Labrador Mix",
                "birth_date": date(2010, 3, 1),
                "weight_kg": Decimal("25.0"),
                "is_spayed_neutered": True,
                "is_microchipped": True,
                "medical_history": {
                    "records": [
                        {
                            "type": "chronic_condition",
                            "description": "Arthritis management",
                            "date": "2023-01-15",
                            "veterinarian": "Dr. Smith",
                            "diagnosis": "Osteoarthritis",
                            "treatment": "Pain management medication",
                            "follow_up_needed": True,
                        }
                    ]
                },
            },
        }

    @staticmethod
    def get_appointment_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get various appointment test scenarios."""
        base_date = datetime.now()

        return {
            "routine_checkup": {
                "scheduled_at": base_date + timedelta(days=7),
                "duration_minutes": 30,
                "service_type": "checkup",
                "status": AppointmentStatus.SCHEDULED,
                "notes": "Annual wellness exam",
                "estimated_cost": Decimal("75.00"),
            },
            "emergency_visit": {
                "scheduled_at": base_date + timedelta(hours=2),
                "duration_minutes": 60,
                "service_type": "emergency",
                "status": AppointmentStatus.CONFIRMED,
                "notes": "Pet ingested foreign object",
                "estimated_cost": Decimal("250.00"),
            },
            "follow_up": {
                "scheduled_at": base_date + timedelta(days=14),
                "duration_minutes": 20,
                "service_type": "follow_up",
                "status": AppointmentStatus.SCHEDULED,
                "notes": "Post-surgery check",
                "estimated_cost": Decimal("50.00"),
            },
            "completed_visit": {
                "scheduled_at": base_date - timedelta(days=30),
                "duration_minutes": 45,
                "service_type": "checkup",
                "status": AppointmentStatus.COMPLETED,
                "notes": "Vaccination and health check",
                "estimated_cost": Decimal("85.00"),
                "actual_cost": Decimal("90.00"),
            },
        }


async def wait_for_condition(
    condition_func,
    timeout_seconds: float = 5.0,
    check_interval: float = 0.1,
    error_message: str = "Condition not met within timeout",
):
    """
    Wait for a condition to become true within a timeout period.

    Args:
        condition_func: Function that returns True when condition is met
        timeout_seconds: Maximum time to wait
        check_interval: Time between checks
        error_message: Error message if timeout is reached

    Raises:
        AssertionError: If condition is not met within timeout
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        if (
            await condition_func()
            if asyncio.iscoroutinefunction(condition_func)
            else condition_func()
        ):
            return

        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout_seconds:
            raise AssertionError(f"{error_message} (waited {timeout_seconds}s)")

        await asyncio.sleep(check_interval)


def create_test_id() -> str:
    """Create a unique test identifier."""
    return f"test_{uuid.uuid4().hex[:8]}"


def create_test_email(prefix: str = "test") -> str:
    """Create a unique test email address."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def create_test_phone() -> str:
    """Create a test phone number."""
    import random

    return f"+1{random.randint(1000000000, 9999999999)}"
