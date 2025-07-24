#!/usr/bin/env python3
"""
Basic usage examples for the vet-core package.

This example demonstrates the most common usage patterns for the vet-core package,
including model creation, database operations, schema validation, and basic
error handling.
"""

import asyncio
import os
from datetime import datetime, date
from typing import List, Optional

from vet_core import (
    get_session,
    get_transaction,
    create_engine,
    User, Pet, Appointment, Clinic, Veterinarian,
    ValidationException, DatabaseException
)
from vet_core.schemas import (
    UserCreate, UserResponse,
    PetCreate, PetResponse,
    AppointmentCreate, AppointmentResponse,
    ClinicCreate, ClinicResponse,
    VeterinarianCreate, VeterinarianResponse
)
from vet_core.models import UserRole, PetSpecies, AppointmentStatus, ServiceType


async def setup_database():
    """Set up database connection for examples."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/vet_clinic_dev"
    )
    
    engine = create_engine(database_url, echo=False)
    return engine


async def create_user_example():
    """Example: Creating and validating a user."""
    print("\n=== Creating User Example ===")
    
    # 1. Create user data with Pydantic schema validation
    try:
        user_data = UserCreate(
            clerk_user_id="clerk_user_123",
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.PET_OWNER,
            phone_number="+1-555-0123",
            preferences={
                "notifications": {"email": True, "sms": False},
                "language": "en",
                "timezone": "America/New_York"
            }
        )
        print(f"✓ User data validated: {user_data.email}")
        
    except ValidationException as e:
        print(f"✗ Validation failed: {e}")
        return None
    
    # 2. Create user in database
    try:
        async with get_transaction() as session:
            # Convert Pydantic model to SQLAlchemy model
            user = User(**user_data.model_dump())
            session.add(user)
            await session.flush()  # Get the ID without committing
            
            # Convert back to response schema
            user_response = UserResponse.model_validate(user)
            print(f"✓ User created with ID: {user_response.id}")
            
            return user_response
            
    except DatabaseException as e:
        print(f"✗ Database error: {e}")
        return None


async def create_pet_example(owner_id: str):
    """Example: Creating a pet with medical history."""
    print("\n=== Creating Pet Example ===")
    
    try:
        pet_data = PetCreate(
            owner_id=owner_id,
            name="Buddy",
            species=PetSpecies.DOG,
            breed="Golden Retriever",
            birth_date=date(2020, 3, 15),
            weight=65.5,
            color="Golden",
            microchip_id="123456789012345",
            medical_history={
                "allergies": ["chicken", "beef"],
                "medications": [
                    {
                        "name": "Heartgard",
                        "dosage": "68mg",
                        "frequency": "monthly",
                        "start_date": "2023-01-01"
                    }
                ],
                "vaccinations": [
                    {
                        "vaccine": "DHPP",
                        "date": "2024-01-15",
                        "next_due": "2025-01-15",
                        "veterinarian": "Dr. Smith"
                    }
                ]
            }
        )
        print(f"✓ Pet data validated: {pet_data.name}")
        
        async with get_transaction() as session:
            pet = Pet(**pet_data.model_dump())
            session.add(pet)
            await session.flush()
            
            pet_response = PetResponse.model_validate(pet)
            print(f"✓ Pet created: {pet_response.name} (ID: {pet_response.id})")
            
            return pet_response
            
    except (ValidationException, DatabaseException) as e:
        print(f"✗ Error creating pet: {e}")
        return None


async def create_clinic_example():
    """Example: Creating a veterinary clinic."""
    print("\n=== Creating Clinic Example ===")
    
    try:
        clinic_data = ClinicCreate(
            name="Happy Paws Veterinary Clinic",
            address="123 Main Street, Anytown, ST 12345",
            phone_number="+1-555-0199",
            email="info@happypaws.com",
            website="https://happypaws.com",
            operating_hours={
                "monday": {"open": "08:00", "close": "18:00"},
                "tuesday": {"open": "08:00", "close": "18:00"},
                "wednesday": {"open": "08:00", "close": "18:00"},
                "thursday": {"open": "08:00", "close": "18:00"},
                "friday": {"open": "08:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "16:00"},
                "sunday": {"closed": True}
            },
            services_offered=[
                "General Checkups",
                "Vaccinations",
                "Surgery",
                "Dental Care",
                "Emergency Care"
            ],
            location={"latitude": 40.7128, "longitude": -74.0060}
        )
        print(f"✓ Clinic data validated: {clinic_data.name}")
        
        async with get_transaction() as session:
            clinic = Clinic(**clinic_data.model_dump())
            session.add(clinic)
            await session.flush()
            
            clinic_response = ClinicResponse.model_validate(clinic)
            print(f"✓ Clinic created: {clinic_response.name} (ID: {clinic_response.id})")
            
            return clinic_response
            
    except (ValidationException, DatabaseException) as e:
        print(f"✗ Error creating clinic: {e}")
        return None


async def create_veterinarian_example(user_id: str, clinic_id: str):
    """Example: Creating a veterinarian profile."""
    print("\n=== Creating Veterinarian Example ===")
    
    try:
        vet_data = VeterinarianCreate(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            specializations=["Small Animal Medicine", "Surgery"],
            education=[
                {
                    "degree": "Doctor of Veterinary Medicine",
                    "school": "University of Veterinary Medicine",
                    "year": 2018
                }
            ],
            experience_years=6,
            availability={
                "monday": [{"start": "09:00", "end": "17:00"}],
                "tuesday": [{"start": "09:00", "end": "17:00"}],
                "wednesday": [{"start": "09:00", "end": "17:00"}],
                "thursday": [{"start": "09:00", "end": "17:00"}],
                "friday": [{"start": "09:00", "end": "15:00"}]
            }
        )
        print(f"✓ Veterinarian data validated: License {vet_data.license_number}")
        
        async with get_transaction() as session:
            veterinarian = Veterinarian(**vet_data.model_dump())
            session.add(veterinarian)
            await session.flush()
            
            vet_response = VeterinarianResponse.model_validate(veterinarian)
            print(f"✓ Veterinarian created: {vet_response.license_number} (ID: {vet_response.id})")
            
            return vet_response
            
    except (ValidationException, DatabaseException) as e:
        print(f"✗ Error creating veterinarian: {e}")
        return None


async def create_appointment_example(pet_id: str, veterinarian_id: str, clinic_id: str):
    """Example: Scheduling an appointment."""
    print("\n=== Creating Appointment Example ===")
    
    try:
        appointment_data = AppointmentCreate(
            pet_id=pet_id,
            veterinarian_id=veterinarian_id,
            clinic_id=clinic_id,
            scheduled_at=datetime(2024, 2, 15, 14, 30),
            service_type=ServiceType.CHECKUP,
            status=AppointmentStatus.SCHEDULED,
            notes="Annual wellness exam and vaccinations",
            estimated_duration_minutes=60,
            estimated_cost=150.00
        )
        print(f"✓ Appointment data validated: {appointment_data.scheduled_at}")
        
        async with get_transaction() as session:
            appointment = Appointment(**appointment_data.model_dump())
            session.add(appointment)
            await session.flush()
            
            appointment_response = AppointmentResponse.model_validate(appointment)
            print(f"✓ Appointment scheduled: {appointment_response.scheduled_at} (ID: {appointment_response.id})")
            
            return appointment_response
            
    except (ValidationException, DatabaseException) as e:
        print(f"✗ Error creating appointment: {e}")
        return None


async def query_examples():
    """Example: Common database queries."""
    print("\n=== Database Query Examples ===")
    
    try:
        async with get_session() as session:
            # 1. Find all pets for a specific owner
            from sqlalchemy import select
            
            # Query pets with their owner information
            stmt = select(Pet).join(User).where(User.email == "john.doe@example.com")
            result = await session.execute(stmt)
            pets = result.scalars().all()
            
            print(f"✓ Found {len(pets)} pets for owner")
            for pet in pets:
                print(f"  - {pet.name} ({pet.species.value})")
            
            # 2. Find upcoming appointments
            from datetime import datetime, timedelta
            
            tomorrow = datetime.now() + timedelta(days=1)
            stmt = select(Appointment).where(
                Appointment.scheduled_at >= datetime.now(),
                Appointment.scheduled_at <= tomorrow,
                Appointment.status == AppointmentStatus.SCHEDULED
            )
            result = await session.execute(stmt)
            appointments = result.scalars().all()
            
            print(f"✓ Found {len(appointments)} upcoming appointments")
            
            # 3. Find clinics by location (example query)
            stmt = select(Clinic).where(Clinic.name.ilike("%happy%"))
            result = await session.execute(stmt)
            clinics = result.scalars().all()
            
            print(f"✓ Found {len(clinics)} clinics matching search")
            
    except DatabaseException as e:
        print(f"✗ Query error: {e}")


async def error_handling_examples():
    """Example: Error handling patterns."""
    print("\n=== Error Handling Examples ===")
    
    # 1. Validation error handling
    try:
        invalid_user = UserCreate(
            email="invalid-email",  # Invalid email format
            first_name="",  # Empty required field
            role="invalid_role"  # Invalid enum value
        )
    except ValidationException as e:
        print(f"✓ Caught validation error: {e.message}")
        print(f"  Field errors: {e.validation_errors}")
    
    # 2. Database constraint violation
    try:
        async with get_transaction() as session:
            # Try to create duplicate user with same email
            user1 = User(
                clerk_user_id="user1",
                email="duplicate@example.com",
                first_name="User",
                last_name="One"
            )
            user2 = User(
                clerk_user_id="user2", 
                email="duplicate@example.com",  # Duplicate email
                first_name="User",
                last_name="Two"
            )
            
            session.add(user1)
            session.add(user2)
            await session.commit()
            
    except DatabaseException as e:
        print(f"✓ Caught database constraint error: {e.message}")
        if e.is_retryable():
            print("  This error is retryable")
        else:
            print("  This error is not retryable")
    
    # 3. Using error response formatting
    from vet_core.exceptions import create_error_response
    
    try:
        raise ValidationException(
            "Pet age validation failed",
            field="age",
            value=-5,
            validation_errors={"age": ["Age must be positive"]}
        )
    except ValidationException as e:
        error_response = create_error_response(e, include_debug=True)
        print(f"✓ Formatted error response: {error_response['error']['type']}")


async def main():
    """Run all basic usage examples."""
    print("🏥 Vet Core Package - Basic Usage Examples")
    print("=" * 60)
    
    # Set up database
    engine = await setup_database()
    
    try:
        # Create entities step by step
        user = await create_user_example()
        if not user:
            print("⚠️  Skipping remaining examples due to user creation failure")
            return
        
        pet = await create_pet_example(user.id)
        clinic = await create_clinic_example()
        
        if pet and clinic:
            # Create a veterinarian user first
            vet_user_data = UserCreate(
                clerk_user_id="vet_user_123",
                email="dr.smith@happypaws.com",
                first_name="Sarah",
                last_name="Smith",
                role=UserRole.VETERINARIAN
            )
            
            async with get_transaction() as session:
                vet_user = User(**vet_user_data.model_dump())
                session.add(vet_user)
                await session.flush()
                
                veterinarian = await create_veterinarian_example(str(vet_user.id), clinic.id)
                
                if veterinarian:
                    appointment = await create_appointment_example(
                        pet.id, veterinarian.id, clinic.id
                    )
        
        # Demonstrate queries
        await query_examples()
        
        # Demonstrate error handling
        await error_handling_examples()
        
    except Exception as e:
        print(f"⚠️  Example failed: {e}")
        print("This is expected if no database is running")
    
    finally:
        await engine.dispose()
    
    print("\n" + "=" * 60)
    print("🎉 Basic usage examples completed!")
    print("\nKey Patterns Demonstrated:")
    print("• Pydantic schema validation for data integrity")
    print("• SQLAlchemy model creation and relationships")
    print("• Async database operations with transactions")
    print("• Common query patterns and joins")
    print("• Comprehensive error handling strategies")
    print("• Response schema serialization")


if __name__ == "__main__":
    print("Starting vet-core basic usage examples...")
    print("Note: Some features require a running PostgreSQL database")
    print("Set DATABASE_URL environment variable to connect to your database")
    print()
    
    asyncio.run(main())