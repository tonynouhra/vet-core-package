"""
Pytest configuration and fixtures for vet-core tests.

This module provides common fixtures and configuration for all tests
in the vet-core package, including database setup, factory classes,
and test data management.
"""

import asyncio
import os
import tempfile
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, Optional

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from vet_core.database.connection import create_engine
from vet_core.database.session import SessionManager
from vet_core.models import (
    Appointment,
    AppointmentPriority,
    AppointmentStatus,
    Clinic,
    ClinicStatus,
    ClinicType,
    EmploymentType,
    LicenseStatus,
    Pet,
    PetGender,
    PetSize,
    PetSpecies,
    PetStatus,
    ServiceType,
    User,
    UserRole,
    UserStatus,
    Veterinarian,
    VeterinarianStatus,
)
from vet_core.models.base import Base

# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/vet_core_test",
)

# SQLite temporary file for fast tests (when PostgreSQL not available)
# Using a temporary file allows tables created in one connection to be visible to others

TEMP_DB_FILE = os.path.join(tempfile.gettempdir(), "vet_core_test.db")
SQLITE_TEST_URL = f"sqlite+aiosqlite:///{TEMP_DB_FILE}"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine with proper configuration.

    Uses in-memory SQLite by default for speed, but can use PostgreSQL
    if TEST_DATABASE_URL is set and available.
    """
    # Try PostgreSQL first if configured
    if TEST_DATABASE_URL.startswith("postgresql"):
        try:
            engine = create_engine(
                TEST_DATABASE_URL,
                use_null_pool=True,  # Don't pool connections in tests
                echo=False,  # Set to True for SQL debugging
            )

            # Test connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            yield engine
            await engine.dispose()
            return

        except Exception as e:
            print(f"PostgreSQL test database not available: {e}")
            print("Falling back to SQLite in-memory database")

    # Fall back to SQLite in-memory
    engine = create_async_engine(
        SQLITE_TEST_URL,
        poolclass=NullPool,
        echo=False,  # Set to True for SQL debugging
        future=True,
    )

    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_manager(
    test_engine: AsyncEngine,
) -> AsyncGenerator[SessionManager, None]:
    """Create a session manager for testing."""
    session_manager = SessionManager(test_engine)

    # Initialize database schema
    # For SQLite in-memory databases, we need to create tables outside of a transaction
    # to ensure they persist and are visible to all connections
    async with test_engine.connect() as conn:
        try:
            print(
                f"Creating tables for {len(Base.metadata.tables)} registered tables..."
            )
            for table_name in Base.metadata.tables.keys():
                print(f"  - {table_name}")
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()  # Ensure tables are committed
            print("Tables created successfully!")

            # Verify tables were created
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            created_tables = [row[0] for row in result.fetchall()]
            print(f"Tables found in database: {created_tables}")
        except Exception as e:
            print(f"Error creating tables: {e}")
            raise

    yield session_manager

    # Cleanup
    await session_manager.close_all_sessions()

    # Remove temporary database file if it exists
    if os.path.exists(TEMP_DB_FILE):
        try:
            os.remove(TEMP_DB_FILE)
        except Exception:
            pass  # Ignore cleanup errors


@pytest_asyncio.fixture
async def async_session(
    test_session_manager: SessionManager,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session for testing with automatic cleanup.

    Each test gets a fresh session that is automatically rolled back
    after the test completes to ensure test isolation.
    """
    async with test_session_manager.get_session() as session:
        # Start a transaction that we'll roll back at the end
        transaction = await session.begin()

        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
            await transaction.rollback()


@pytest_asyncio.fixture
async def async_transaction(
    test_session_manager: SessionManager,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session within a transaction for testing.

    Useful for testing transaction-specific behavior.
    """
    async with test_session_manager.get_transaction() as session:
        yield session


# Factory classes for creating test entities
class UserFactory:
    """Factory for creating test User instances."""

    @staticmethod
    def build(**kwargs) -> User:
        """Build a User instance without saving to database."""
        defaults = {
            "clerk_user_id": f"clerk_{uuid.uuid4().hex[:12]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": UserRole.PET_OWNER,
            "status": UserStatus.ACTIVE,
            "email_verified": True,
            "phone_number": "+1234567890",
            "country": "US",
        }
        defaults.update(kwargs)
        return User(**defaults)

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> User:
        """Create and save a User instance to the database."""
        user = UserFactory.build(**kwargs)
        session.add(user)
        await session.flush()  # Get the ID without committing
        await session.refresh(user)
        return user

    @staticmethod
    def build_veterinarian(**kwargs) -> User:
        """Build a User instance with veterinarian role."""
        defaults = {
            "role": UserRole.VETERINARIAN,
            "first_name": "Dr. Test",
            "last_name": "Veterinarian",
        }
        defaults.update(kwargs)
        return UserFactory.build(**defaults)

    @staticmethod
    async def create_veterinarian(session: AsyncSession, **kwargs) -> User:
        """Create and save a veterinarian User instance."""
        user = UserFactory.build_veterinarian(**kwargs)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    @staticmethod
    def build_admin(**kwargs) -> User:
        """Build a User instance with admin role."""
        defaults = {
            "role": UserRole.PLATFORM_ADMIN,
            "first_name": "Admin",
            "last_name": "User",
        }
        defaults.update(kwargs)
        return UserFactory.build(**defaults)


class PetFactory:
    """Factory for creating test Pet instances."""

    @staticmethod
    def build(owner_id: Optional[uuid.UUID] = None, **kwargs) -> Pet:
        """Build a Pet instance without saving to database."""
        if owner_id is None:
            owner_id = uuid.uuid4()

        defaults = {
            "owner_id": owner_id,
            "name": f"TestPet_{uuid.uuid4().hex[:8]}",
            "species": PetSpecies.DOG,
            "breed": "Golden Retriever",
            "gender": PetGender.MALE,
            "birth_date": date(2020, 1, 1),
            "weight_kg": Decimal("25.5"),
            "size_category": PetSize.MEDIUM,
            "status": PetStatus.ACTIVE,
            "is_spayed_neutered": False,
            "is_microchipped": True,
            "microchip_id": f"chip_{uuid.uuid4().hex[:12]}",
        }
        defaults.update(kwargs)
        return Pet(**defaults)

    @staticmethod
    async def create(
        session: AsyncSession, owner: Optional[User] = None, **kwargs
    ) -> Pet:
        """Create and save a Pet instance to the database."""
        if owner is None:
            owner = await UserFactory.create(session)

        pet = PetFactory.build(owner_id=owner.id, **kwargs)
        session.add(pet)
        await session.flush()
        await session.refresh(pet)
        return pet

    @staticmethod
    def build_cat(**kwargs) -> Pet:
        """Build a Cat Pet instance."""
        defaults = {
            "species": PetSpecies.CAT,
            "breed": "Domestic Shorthair",
            "weight_kg": Decimal("4.5"),
            "size_category": PetSize.SMALL,
        }
        defaults.update(kwargs)
        return PetFactory.build(**defaults)

    @staticmethod
    async def create_cat(
        session: AsyncSession, owner: Optional[User] = None, **kwargs
    ) -> Pet:
        """Create and save a Cat Pet instance."""
        if owner is None:
            owner = await UserFactory.create(session)

        pet = PetFactory.build_cat(owner_id=owner.id, **kwargs)
        session.add(pet)
        await session.flush()
        await session.refresh(pet)
        return pet

    @staticmethod
    def build_with_medical_history(**kwargs) -> Pet:
        """Build a Pet instance with sample medical history."""
        medical_history = {
            "records": [
                {
                    "type": "checkup",
                    "description": "Annual wellness exam",
                    "date": "2023-01-15",
                    "veterinarian": "Dr. Smith",
                    "diagnosis": "Healthy",
                    "treatment": "None required",
                    "follow_up_needed": False,
                    "recorded_at": datetime.utcnow().isoformat(),
                }
            ]
        }

        vaccination_records = [
            {
                "vaccine_type": "DHPP",
                "date": "2023-01-15",
                "veterinarian": "Dr. Smith",
                "batch_number": "VAC123456",
                "next_due_date": "2024-01-15",
                "notes": "No adverse reactions",
                "recorded_at": datetime.utcnow().isoformat(),
            }
        ]

        defaults = {
            "medical_history": medical_history,
            "vaccination_records": vaccination_records,
        }
        defaults.update(kwargs)
        return PetFactory.build(**defaults)


class ClinicFactory:
    """Factory for creating test Clinic instances."""

    @staticmethod
    def build(**kwargs) -> Clinic:
        """Build a Clinic instance without saving to database."""
        defaults = {
            "name": f"Test Clinic {uuid.uuid4().hex[:8]}",
            "address": "123 Test Street",
            "city": "Test City",
            "state": "CA",
            "postal_code": "12345",
            "country": "US",
            "phone": "+1234567890",
            "email": f"clinic_{uuid.uuid4().hex[:8]}@example.com",
            "status": ClinicStatus.ACTIVE,
            "clinic_type": ClinicType.GENERAL_PRACTICE,
            "operating_hours": {
                "monday": {"open": "08:00", "close": "18:00"},
                "tuesday": {"open": "08:00", "close": "18:00"},
                "wednesday": {"open": "08:00", "close": "18:00"},
                "thursday": {"open": "08:00", "close": "18:00"},
                "friday": {"open": "08:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "17:00"},
                "sunday": {"closed": True},
            },
        }
        defaults.update(kwargs)
        return Clinic(**defaults)

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Clinic:
        """Create and save a Clinic instance to the database."""
        clinic = ClinicFactory.build(**kwargs)
        session.add(clinic)
        await session.flush()
        await session.refresh(clinic)
        return clinic


class VeterinarianFactory:
    """Factory for creating test Veterinarian instances."""

    @staticmethod
    def build(
        user_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> Veterinarian:
        """Build a Veterinarian instance without saving to database."""
        if user_id is None:
            user_id = uuid.uuid4()
        if clinic_id is None:
            clinic_id = uuid.uuid4()

        defaults = {
            "user_id": user_id,
            "clinic_id": clinic_id,
            "license_number": f"VET{uuid.uuid4().hex[:8].upper()}",
            "license_state": "CA",
            "license_expiry": date(2025, 12, 31),
            "license_status": LicenseStatus.ACTIVE,
            "status": VeterinarianStatus.ACTIVE,
            "employment_type": EmploymentType.FULL_TIME,
            "specializations": ["General Practice"],
            "years_experience": 5,
            "education": "DVM from UC Davis",
            "rating": Decimal("4.5"),
        }
        defaults.update(kwargs)
        return Veterinarian(**defaults)

    @staticmethod
    async def create(
        session: AsyncSession,
        user: Optional[User] = None,
        clinic: Optional[Clinic] = None,
        **kwargs,
    ) -> Veterinarian:
        """Create and save a Veterinarian instance to the database."""
        if user is None:
            user = await UserFactory.create_veterinarian(session)
        if clinic is None:
            clinic = await ClinicFactory.create(session)

        veterinarian = VeterinarianFactory.build(
            user_id=user.id, clinic_id=clinic.id, **kwargs
        )
        session.add(veterinarian)
        await session.flush()
        await session.refresh(veterinarian)
        return veterinarian


class AppointmentFactory:
    """Factory for creating test Appointment instances."""

    @staticmethod
    def build(
        pet_id: Optional[uuid.UUID] = None,
        veterinarian_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> Appointment:
        """Build an Appointment instance without saving to database."""
        if pet_id is None:
            pet_id = uuid.uuid4()
        if veterinarian_id is None:
            veterinarian_id = uuid.uuid4()
        if clinic_id is None:
            clinic_id = uuid.uuid4()

        defaults = {
            "pet_id": pet_id,
            "veterinarian_id": veterinarian_id,
            "clinic_id": clinic_id,
            "scheduled_at": datetime(2024, 6, 15, 10, 0, 0),
            "duration_minutes": 30,
            "service_type": ServiceType.CHECKUP,
            "status": AppointmentStatus.SCHEDULED,
            "priority": AppointmentPriority.NORMAL,
            "notes": "Regular checkup appointment",
            "estimated_cost": Decimal("75.00"),
        }
        defaults.update(kwargs)
        return Appointment(**defaults)

    @staticmethod
    async def create(
        session: AsyncSession,
        pet: Optional[Pet] = None,
        veterinarian: Optional[Veterinarian] = None,
        clinic: Optional[Clinic] = None,
        **kwargs,
    ) -> Appointment:
        """Create and save an Appointment instance to the database."""
        if pet is None:
            pet = await PetFactory.create(session)
        if veterinarian is None:
            veterinarian = await VeterinarianFactory.create(session)
        if clinic is None:
            clinic = await ClinicFactory.create(session)

        appointment = AppointmentFactory.build(
            pet_id=pet.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            **kwargs,
        )
        session.add(appointment)
        await session.flush()
        await session.refresh(appointment)
        return appointment


# Fixture factories
@pytest.fixture
def user_factory() -> UserFactory:
    """Factory for creating test users."""
    return UserFactory


@pytest.fixture
def pet_factory() -> PetFactory:
    """Factory for creating test pets."""
    return PetFactory


@pytest.fixture
def clinic_factory() -> ClinicFactory:
    """Factory for creating test clinics."""
    return ClinicFactory


@pytest.fixture
def veterinarian_factory() -> VeterinarianFactory:
    """Factory for creating test veterinarians."""
    return VeterinarianFactory


@pytest.fixture
def appointment_factory() -> AppointmentFactory:
    """Factory for creating test appointments."""
    return AppointmentFactory


# Common test data fixtures
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user for use in tests."""
    return await UserFactory.create(async_session)


@pytest_asyncio.fixture
async def test_veterinarian_user(async_session: AsyncSession) -> User:
    """Create a test veterinarian user for use in tests."""
    return await UserFactory.create_veterinarian(async_session)


@pytest_asyncio.fixture
async def test_pet(async_session: AsyncSession, test_user: User) -> Pet:
    """Create a test pet for use in tests."""
    return await PetFactory.create(async_session, owner=test_user)


@pytest_asyncio.fixture
async def test_clinic(async_session: AsyncSession) -> Clinic:
    """Create a test clinic for use in tests."""
    return await ClinicFactory.create(async_session)


@pytest_asyncio.fixture
async def test_veterinarian(
    async_session: AsyncSession, test_veterinarian_user: User, test_clinic: Clinic
) -> Veterinarian:
    """Create a test veterinarian for use in tests."""
    return await VeterinarianFactory.create(
        async_session, user=test_veterinarian_user, clinic=test_clinic
    )


@pytest_asyncio.fixture
async def test_appointment(
    async_session: AsyncSession,
    test_pet: Pet,
    test_veterinarian: Veterinarian,
    test_clinic: Clinic,
) -> Appointment:
    """Create a test appointment for use in tests."""
    return await AppointmentFactory.create(
        async_session, pet=test_pet, veterinarian=test_veterinarian, clinic=test_clinic
    )


# Database cleanup utilities
@pytest_asyncio.fixture
async def clean_database(test_session_manager: SessionManager):
    """
    Fixture that provides database cleanup functionality.

    Can be used to clean specific tables or reset the entire database
    state between tests when needed.
    """

    class DatabaseCleaner:
        def __init__(self, session_manager: SessionManager):
            self.session_manager = session_manager

        async def clean_table(self, table_name: str):
            """Clean a specific table."""
            async with self.session_manager.get_session() as session:
                await session.execute(text(f"DELETE FROM {table_name}"))
                await session.commit()

        async def clean_all_tables(self):
            """Clean all tables in dependency order."""
            tables = ["appointments", "veterinarians", "pets", "clinics", "users"]

            async with self.session_manager.get_session() as session:
                for table in tables:
                    await session.execute(text(f"DELETE FROM {table}"))
                await session.commit()

        async def reset_sequences(self):
            """Reset auto-increment sequences (PostgreSQL specific)."""
            async with self.session_manager.get_session() as session:
                # This is PostgreSQL specific - would need adaptation for other DBs
                try:
                    await session.execute(
                        text(
                            """
                        SELECT setval(pg_get_serial_sequence(schemaname||'.'||tablename, columnname), 1, false)
                        FROM pg_tables t
                        JOIN pg_attribute a ON a.attrelid = (schemaname||'.'||tablename)::regclass
                        WHERE schemaname = 'public' AND a.atthasdef AND pg_get_expr(d.adbin, d.adrelid) LIKE '%nextval%'
                        AND d.adrelid = a.attrelid AND d.adnum = a.attnum
                        JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum;
                    """
                        )
                    )
                    await session.commit()
                except Exception:
                    # Ignore errors for non-PostgreSQL databases
                    pass

    return DatabaseCleaner(test_session_manager)


# Test isolation utilities
@pytest.fixture(autouse=True)
async def isolate_tests(async_session: AsyncSession):
    """
    Automatically isolate tests by ensuring each test starts with a clean state.

    This fixture runs automatically for every test and ensures proper isolation.
    """
    # The async_session fixture already handles transaction rollback,
    # so we just need to ensure any global state is reset
    yield

    # Any cleanup that needs to happen after each test can go here
    pass


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """
    Fixture that provides performance monitoring utilities for tests.
    """
    import time
    from contextlib import contextmanager

    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}

        @contextmanager
        def measure(self, operation_name: str):
            """Context manager to measure operation performance."""
            start_time = time.time()
            try:
                yield
            finally:
                end_time = time.time()
                duration = end_time - start_time
                if operation_name not in self.measurements:
                    self.measurements[operation_name] = []
                self.measurements[operation_name].append(duration)

        def get_average_time(self, operation_name: str) -> float:
            """Get average time for an operation."""
            times = self.measurements.get(operation_name, [])
            return sum(times) / len(times) if times else 0.0

        def get_total_time(self, operation_name: str) -> float:
            """Get total time for an operation."""
            return sum(self.measurements.get(operation_name, []))

        def reset(self):
            """Reset all measurements."""
            self.measurements.clear()

    return PerformanceMonitor()


# Mock data generators
@pytest.fixture
def mock_data_generator():
    """
    Fixture that provides utilities for generating mock data for tests.
    """
    import random

    from faker import Faker

    fake = Faker()

    class MockDataGenerator:
        def __init__(self):
            self.fake = fake

        def generate_user_data(self, **overrides) -> Dict[str, Any]:
            """Generate realistic user data."""
            data = {
                "clerk_user_id": f"clerk_{uuid.uuid4().hex[:12]}",
                "email": self.fake.email(),
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "phone_number": self.fake.phone_number(),
                "address_line1": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state_abbr(),
                "postal_code": self.fake.zipcode(),
                "country": "US",
                "role": random.choice(list(UserRole)),
                "status": UserStatus.ACTIVE,
            }
            data.update(overrides)
            return data

        def generate_pet_data(self, owner_id: uuid.UUID, **overrides) -> Dict[str, Any]:
            """Generate realistic pet data."""
            species = random.choice(list(PetSpecies))

            # Species-appropriate names and breeds
            if species == PetSpecies.DOG:
                name = random.choice(
                    ["Buddy", "Max", "Bella", "Lucy", "Charlie", "Daisy"]
                )
                breed = random.choice(
                    ["Golden Retriever", "Labrador", "German Shepherd", "Bulldog"]
                )
                weight = Decimal(str(random.uniform(5, 50)))
            elif species == PetSpecies.CAT:
                name = random.choice(
                    ["Whiskers", "Mittens", "Shadow", "Luna", "Oliver", "Chloe"]
                )
                breed = random.choice(
                    ["Domestic Shorthair", "Persian", "Siamese", "Maine Coon"]
                )
                weight = Decimal(str(random.uniform(2, 8)))
            else:
                name = self.fake.first_name()
                breed = None
                weight = Decimal(str(random.uniform(0.1, 10)))

            data = {
                "owner_id": owner_id,
                "name": name,
                "species": species,
                "breed": breed,
                "gender": random.choice(list(PetGender)),
                "birth_date": self.fake.date_between(start_date="-15y", end_date="-1m"),
                "weight_kg": weight,
                "status": PetStatus.ACTIVE,
                "is_spayed_neutered": random.choice([True, False]),
                "is_microchipped": random.choice([True, False]),
            }
            data.update(overrides)
            return data

        def generate_clinic_data(self, **overrides) -> Dict[str, Any]:
            """Generate realistic clinic data."""
            data = {
                "name": f"{self.fake.last_name()} Veterinary Clinic",
                "address": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state_abbr(),
                "postal_code": self.fake.zipcode(),
                "country": "US",
                "phone": self.fake.phone_number(),
                "email": self.fake.email(),
                "status": ClinicStatus.ACTIVE,
                "clinic_type": random.choice(list(ClinicType)),
            }
            data.update(overrides)
            return data

    return MockDataGenerator()
