#!/usr/bin/env python3
"""
Advanced usage patterns for the vet-core package.

This example demonstrates advanced patterns including:
- Complex queries with joins and aggregations
- Bulk operations and batch processing
- Custom validation and business rules
- Advanced error handling and retry mechanisms
- Performance optimization techniques
- Testing patterns with factories
"""

import asyncio
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from vet_core import (
    get_session,
    get_transaction,
    create_engine,
    User, Pet, Appointment, Clinic, Veterinarian,
    ValidationException, DatabaseException
)
from vet_core.schemas import (
    UserCreate, PetCreate, AppointmentCreate,
    AppointmentListResponse, PetResponse
)
from vet_core.models import (
    UserRole, PetSpecies, AppointmentStatus, ServiceType,
    PetGender, PetSize, ClinicStatus
)
from vet_core.utils import datetime_utils, validation
from vet_core.exceptions import (
    BusinessRuleException,
    handle_database_retry
)


async def complex_query_examples():
    """Demonstrate complex database queries with joins and aggregations."""
    print("\n=== Complex Query Examples ===")
    
    async with get_session() as session:
        try:
            # 1. Find veterinarians with their appointment statistics
            stmt = (
                select(
                    Veterinarian,
                    func.count(Appointment.id).label('total_appointments'),
                    func.avg(Appointment.estimated_cost).label('avg_cost'),
                    func.max(Appointment.scheduled_at).label('last_appointment')
                )
                .outerjoin(Appointment)
                .group_by(Veterinarian.id)
                .options(joinedload(Veterinarian.user))
            )
            
            result = await session.execute(stmt)
            vet_stats = result.all()
            
            print(f"✓ Found {len(vet_stats)} veterinarians with statistics")
            for vet, total, avg_cost, last_appt in vet_stats:
                print(f"  - Dr. {vet.user.last_name}: {total or 0} appointments, "
                      f"avg cost: ${avg_cost or 0:.2f}")
            
            # 2. Find pets with upcoming appointments and their medical history
            next_week = datetime.now() + timedelta(days=7)
            stmt = (
                select(Pet)
                .join(Appointment)
                .where(
                    and_(
                        Appointment.scheduled_at.between(datetime.now(), next_week),
                        Appointment.status == AppointmentStatus.SCHEDULED
                    )
                )
                .options(
                    selectinload(Pet.owner),
                    selectinload(Pet.appointments)
                )
                .distinct()
            )
            
            result = await session.execute(stmt)
            pets_with_appointments = result.scalars().all()
            
            print(f"✓ Found {len(pets_with_appointments)} pets with upcoming appointments")
            
            # 3. Clinic utilization analysis
            stmt = (
                select(
                    Clinic.name,
                    func.count(Appointment.id).label('appointment_count'),
                    func.sum(Appointment.estimated_cost).label('total_revenue'),
                    func.avg(Appointment.estimated_duration_minutes).label('avg_duration')
                )
                .join(Appointment)
                .where(Appointment.scheduled_at >= datetime.now() - timedelta(days=30))
                .group_by(Clinic.id, Clinic.name)
                .order_by(desc('appointment_count'))
            )
            
            result = await session.execute(stmt)
            clinic_stats = result.all()
            
            print(f"✓ Clinic utilization analysis (last 30 days):")
            for name, count, revenue, avg_duration in clinic_stats:
                print(f"  - {name}: {count} appointments, "
                      f"${revenue or 0:.2f} revenue, {avg_duration or 0:.1f}min avg")
                      
        except DatabaseException as e:
            print(f"✗ Query error: {e}")


async def bulk_operations_example():
    """Demonstrate bulk operations and batch processing."""
    print("\n=== Bulk Operations Example ===")
    
    try:
        # 1. Bulk create multiple pets
        pets_data = [
            {
                "name": f"Pet_{i}",
                "species": PetSpecies.DOG if i % 2 == 0 else PetSpecies.CAT,
                "breed": "Mixed Breed",
                "birth_date": date(2020 + (i % 4), 1 + (i % 12), 1),
                "weight": 10.0 + i,
                "gender": PetGender.MALE if i % 2 == 0 else PetGender.FEMALE
            }
            for i in range(5)
        ]
        
        async with get_transaction() as session:
            # Create pets in batch
            pets = [Pet(**pet_data) for pet_data in pets_data]
            session.add_all(pets)
            await session.flush()
            
            print(f"✓ Bulk created {len(pets)} pets")
            
            # 2. Bulk update operation
            from sqlalchemy import update
            
            # Update all dogs to have a specific size
            stmt = (
                update(Pet)
                .where(Pet.species == PetSpecies.DOG)
                .values(size=PetSize.MEDIUM)
            )
            result = await session.execute(stmt)
            print(f"✓ Bulk updated {result.rowcount} dogs")
            
            # 3. Batch appointment creation with validation
            appointments_data = []
            base_time = datetime.now() + timedelta(days=1)
            
            for i, pet in enumerate(pets[:3]):  # Create appointments for first 3 pets
                appointment_time = base_time + timedelta(hours=i)
                appointments_data.append({
                    "pet_id": pet.id,
                    "scheduled_at": appointment_time,
                    "service_type": ServiceType.CHECKUP,
                    "status": AppointmentStatus.SCHEDULED,
                    "estimated_duration_minutes": 30,
                    "estimated_cost": Decimal("75.00")
                })
            
            appointments = [Appointment(**appt_data) for appt_data in appointments_data]
            session.add_all(appointments)
            
            print(f"✓ Batch created {len(appointments)} appointments")
            
    except (ValidationException, DatabaseException) as e:
        print(f"✗ Bulk operation error: {e}")


async def custom_validation_example():
    """Demonstrate custom validation and business rules."""
    print("\n=== Custom Validation Example ===")
    
    # 1. Custom pet age validation
    def validate_pet_age(birth_date: date) -> None:
        """Validate that pet age is reasonable."""
        today = date.today()
        age_years = (today - birth_date).days / 365.25
        
        if age_years < 0:
            raise ValidationException(
                "Pet birth date cannot be in the future",
                field="birth_date",
                value=birth_date
            )
        
        if age_years > 30:  # Very old for most pets
            raise ValidationException(
                "Pet age seems unrealistic (over 30 years)",
                field="birth_date", 
                value=birth_date,
                validation_errors={"birth_date": [f"Age calculated as {age_years:.1f} years"]}
            )
    
    # 2. Business rule: Appointment scheduling validation
    async def validate_appointment_scheduling(
        session,
        veterinarian_id: str,
        scheduled_at: datetime,
        duration_minutes: int = 30
    ) -> None:
        """Validate appointment scheduling business rules."""
        
        # Check for conflicts
        end_time = scheduled_at + timedelta(minutes=duration_minutes)
        
        stmt = select(Appointment).where(
            and_(
                Appointment.veterinarian_id == veterinarian_id,
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                or_(
                    # New appointment starts during existing appointment
                    and_(
                        Appointment.scheduled_at <= scheduled_at,
                        Appointment.scheduled_at + 
                        func.interval('1 minute') * Appointment.estimated_duration_minutes > scheduled_at
                    ),
                    # New appointment ends during existing appointment
                    and_(
                        Appointment.scheduled_at < end_time,
                        Appointment.scheduled_at + 
                        func.interval('1 minute') * Appointment.estimated_duration_minutes >= end_time
                    )
                )
            )
        )
        
        result = await session.execute(stmt)
        conflicts = result.scalars().all()
        
        if conflicts:
            raise BusinessRuleException(
                "Appointment conflicts with existing booking",
                rule_name="appointment_conflict_check",
                context={
                    "veterinarian_id": veterinarian_id,
                    "requested_time": scheduled_at.isoformat(),
                    "conflicts": [str(appt.id) for appt in conflicts]
                }
            )
    
    # Test custom validations
    try:
        # Test pet age validation
        future_date = date.today() + timedelta(days=30)
        validate_pet_age(future_date)
    except ValidationException as e:
        print(f"✓ Caught future birth date validation: {e.message}")
    
    try:
        # Test very old pet
        old_date = date(1990, 1, 1)
        validate_pet_age(old_date)
    except ValidationException as e:
        print(f"✓ Caught unrealistic age validation: {e.message}")
    
    # Test appointment conflict validation
    async with get_session() as session:
        try:
            # This would normally check against real data
            print("✓ Appointment conflict validation ready (requires real data)")
        except Exception as e:
            print(f"✗ Appointment validation error: {e}")


async def retry_mechanism_example():
    """Demonstrate advanced error handling and retry mechanisms."""
    print("\n=== Retry Mechanism Example ===")
    
    # 1. Custom retry decorator usage
    @handle_database_retry("pet_creation_with_retry", max_retries=3, base_delay=0.1)
    async def create_pet_with_retry(pet_data: dict, should_fail: bool = False):
        """Create pet with automatic retry on database errors."""
        if should_fail:
            raise DatabaseException(
                "Simulated transient database error",
                retry_count=0,
                max_retries=3
            )
        
        async with get_transaction() as session:
            pet = Pet(**pet_data)
            session.add(pet)
            await session.flush()
            return str(pet.id)
    
    # Test successful operation
    pet_data = {
        "name": "Retry Test Pet",
        "species": PetSpecies.DOG,
        "breed": "Test Breed",
        "birth_date": date(2022, 1, 1),
        "weight": 25.0
    }
    
    try:
        pet_id = await create_pet_with_retry(pet_data, should_fail=False)
        print(f"✓ Pet created successfully with retry mechanism: {pet_id}")
    except Exception as e:
        print(f"✗ Pet creation failed: {e}")
    
    # Test retry mechanism
    try:
        await create_pet_with_retry(pet_data, should_fail=True)
    except DatabaseException as e:
        print(f"✓ Retry mechanism exhausted as expected: {e.retry_count} attempts")
    
    # 2. Manual retry with exponential backoff
    async def manual_retry_example():
        """Example of manual retry implementation."""
        max_attempts = 3
        base_delay = 0.1
        
        for attempt in range(max_attempts):
            try:
                # Simulate operation that might fail
                if attempt < 2:  # Fail first 2 attempts
                    raise DatabaseException(f"Attempt {attempt + 1} failed")
                
                print(f"✓ Operation succeeded on attempt {attempt + 1}")
                break
                
            except DatabaseException as e:
                if attempt == max_attempts - 1:
                    print(f"✗ All {max_attempts} attempts failed")
                    raise
                
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"  Attempt {attempt + 1} failed, retrying in {delay}s...")
                await asyncio.sleep(delay)
    
    await manual_retry_example()


async def performance_optimization_example():
    """Demonstrate performance optimization techniques."""
    print("\n=== Performance Optimization Example ===")
    
    async with get_session() as session:
        try:
            # 1. Eager loading to avoid N+1 queries
            print("1. Eager loading optimization:")
            
            # Bad: N+1 query problem
            stmt = select(Pet).limit(5)
            result = await session.execute(stmt)
            pets = result.scalars().all()
            
            # This would cause N additional queries
            # for pet in pets:
            #     print(f"Pet: {pet.name}, Owner: {pet.owner.first_name}")
            
            # Good: Eager loading
            stmt = select(Pet).options(joinedload(Pet.owner)).limit(5)
            result = await session.execute(stmt)
            pets_with_owners = result.unique().scalars().all()
            
            print(f"✓ Loaded {len(pets_with_owners)} pets with owners in single query")
            
            # 2. Batch loading for collections
            print("2. Batch loading optimization:")
            
            stmt = (
                select(User)
                .where(User.role == UserRole.PET_OWNER)
                .options(selectinload(User.pets))
                .limit(3)
            )
            result = await session.execute(stmt)
            owners = result.scalars().all()
            
            total_pets = sum(len(owner.pets) for owner in owners)
            print(f"✓ Loaded {len(owners)} owners with {total_pets} pets using batch loading")
            
            # 3. Pagination for large result sets
            print("3. Pagination example:")
            
            page_size = 10
            offset = 0
            
            stmt = (
                select(Pet)
                .order_by(Pet.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )
            result = await session.execute(stmt)
            page_pets = result.scalars().all()
            
            print(f"✓ Paginated query returned {len(page_pets)} pets")
            
            # 4. Aggregation queries for statistics
            print("4. Aggregation optimization:")
            
            stmt = select(
                func.count(Pet.id).label('total_pets'),
                func.count(Pet.id).filter(Pet.species == PetSpecies.DOG).label('dogs'),
                func.count(Pet.id).filter(Pet.species == PetSpecies.CAT).label('cats'),
                func.avg(Pet.weight).label('avg_weight')
            )
            result = await session.execute(stmt)
            stats = result.first()
            
            if stats:
                print(f"✓ Pet statistics: {stats.total_pets} total, "
                      f"{stats.dogs} dogs, {stats.cats} cats, "
                      f"avg weight: {stats.avg_weight or 0:.1f}lbs")
            
        except DatabaseException as e:
            print(f"✗ Performance optimization error: {e}")


async def testing_patterns_example():
    """Demonstrate testing patterns with factories."""
    print("\n=== Testing Patterns Example ===")
    
    # 1. Simple factory pattern
    class UserFactory:
        """Factory for creating test users."""
        
        @staticmethod
        def create(**kwargs) -> User:
            defaults = {
                "clerk_user_id": f"test_user_{datetime.now().timestamp()}",
                "email": f"test_{datetime.now().timestamp()}@example.com",
                "first_name": "Test",
                "last_name": "User",
                "role": UserRole.PET_OWNER
            }
            defaults.update(kwargs)
            return User(**defaults)
    
    class PetFactory:
        """Factory for creating test pets."""
        
        @staticmethod
        def create(owner_id: Optional[str] = None, **kwargs) -> Pet:
            defaults = {
                "name": f"TestPet_{datetime.now().timestamp()}",
                "species": PetSpecies.DOG,
                "breed": "Test Breed",
                "birth_date": date(2020, 1, 1),
                "weight": 25.0,
                "owner_id": owner_id
            }
            defaults.update(kwargs)
            return Pet(**defaults)
    
    # 2. Use factories in tests
    async with get_transaction() as session:
        try:
            # Create test data using factories
            test_user = UserFactory.create(
                first_name="Factory",
                last_name="User"
            )
            session.add(test_user)
            await session.flush()
            
            test_pet = PetFactory.create(
                owner_id=test_user.id,
                name="Factory Pet",
                species=PetSpecies.CAT
            )
            session.add(test_pet)
            await session.flush()
            
            print(f"✓ Created test user: {test_user.email}")
            print(f"✓ Created test pet: {test_pet.name} owned by {test_user.first_name}")
            
            # 3. Batch factory creation
            batch_pets = [
                PetFactory.create(
                    owner_id=test_user.id,
                    name=f"BatchPet_{i}",
                    species=PetSpecies.DOG if i % 2 == 0 else PetSpecies.CAT
                )
                for i in range(3)
            ]
            
            session.add_all(batch_pets)
            print(f"✓ Created {len(batch_pets)} pets using batch factory pattern")
            
        except DatabaseException as e:
            print(f"✗ Testing pattern error: {e}")


async def main():
    """Run all advanced pattern examples."""
    print("🏥 Vet Core Package - Advanced Patterns Examples")
    print("=" * 60)
    
    # Set up database
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/vet_clinic_dev"
    )
    engine = create_engine(database_url, echo=False)
    
    try:
        await complex_query_examples()
        await bulk_operations_example()
        await custom_validation_example()
        await retry_mechanism_example()
        await performance_optimization_example()
        await testing_patterns_example()
        
    except Exception as e:
        print(f"⚠️  Advanced examples failed: {e}")
        print("This is expected if no database is running or tables don't exist")
    
    finally:
        await engine.dispose()
    
    print("\n" + "=" * 60)
    print("🎉 Advanced patterns examples completed!")
    print("\nAdvanced Patterns Demonstrated:")
    print("• Complex queries with joins and aggregations")
    print("• Bulk operations and batch processing")
    print("• Custom validation and business rules")
    print("• Retry mechanisms with exponential backoff")
    print("• Performance optimization techniques")
    print("• Testing patterns with factory classes")
    print("• Eager loading and N+1 query prevention")
    print("• Pagination and result set management")


if __name__ == "__main__":
    print("Starting vet-core advanced patterns examples...")
    print("Note: These examples require a running PostgreSQL database with tables")
    print("Set DATABASE_URL environment variable to connect to your database")
    print()
    
    asyncio.run(main())