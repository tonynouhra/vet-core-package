# Vet Core Package Usage Guide

This comprehensive guide covers common usage patterns, best practices, and advanced techniques for the vet-core package.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Database Setup](#database-setup)
3. [Basic Operations](#basic-operations)
4. [Advanced Patterns](#advanced-patterns)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)
7. [Testing](#testing)
8. [Best Practices](#best-practices)

## Getting Started

### Installation

```bash
# Basic installation
pip install vet-core

# With development dependencies
pip install vet-core[dev]

# With documentation dependencies
pip install vet-core[docs]
```

### Environment Setup

Create a `.env` file in your project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vetclinic
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DEBUG=false
```

### Basic Import Pattern

```python
# Core imports
from vet_core import (
    get_session, get_transaction, create_engine,
    User, Pet, Appointment, Clinic, Veterinarian
)

# Schema imports
from vet_core.schemas import (
    UserCreate, UserResponse,
    PetCreate, PetResponse,
    AppointmentCreate, AppointmentResponse
)

# Utility imports
from vet_core.utils import datetime_utils, validation
from vet_core.exceptions import VetCoreException, ValidationException
```

## Database Setup

### Engine Configuration

```python
import os
from vet_core import create_engine

# Basic configuration
database_url = os.getenv("DATABASE_URL")
engine = create_engine(database_url)

# Advanced configuration
engine = create_engine(
    database_url,
    pool_size=10,           # Base connection pool size
    max_overflow=20,        # Additional connections beyond pool_size
    pool_timeout=30,        # Timeout for getting connection from pool
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Validate connections before use
    echo=False,             # Set to True for SQL logging
    echo_pool=False,        # Set to True for connection pool logging
)
```

### Database Initialization

```python
from vet_core.database import initialize_database, health_check
from vet_core.models import Base

async def setup_database():
    """Initialize database and run health checks."""
    
    # Check database health
    health_status = await health_check()
    if health_status['status'] != 'healthy':
        raise Exception("Database is not healthy")
    
    # Initialize tables (in development)
    # Note: Use Alembic migrations in production
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database initialized successfully")
```

### Migration Management

```bash
# Initialize Alembic (already done in package)
alembic init alembic

# Create new migration
alembic revision --autogenerate -m "Add new field to User model"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Basic Operations

### Creating Records

```python
async def create_user_and_pet():
    """Example of creating related records."""
    
    # Validate input data with Pydantic
    user_data = UserCreate(
        clerk_user_id="clerk_123",
        email="owner@example.com",
        first_name="John",
        last_name="Doe",
        role=UserRole.PET_OWNER,
        preferences={
            "notifications": {"email": True, "sms": False},
            "language": "en"
        }
    )
    
    # Create user in transaction
    async with get_transaction() as session:
        # Convert Pydantic model to SQLAlchemy model
        user = User(**user_data.model_dump())
        session.add(user)
        await session.flush()  # Get ID without committing
        
        # Create pet for the user
        pet_data = PetCreate(
            owner_id=user.id,
            name="Buddy",
            species=PetSpecies.DOG,
            breed="Golden Retriever",
            birth_date=date(2020, 3, 15),
            medical_history={
                "allergies": ["chicken"],
                "vaccinations": [
                    {
                        "vaccine": "DHPP",
                        "date": "2024-01-15",
                        "next_due": "2025-01-15"
                    }
                ]
            }
        )
        
        pet = Pet(**pet_data.model_dump())
        session.add(pet)
        
        # Transaction automatically commits on success
        print(f"Created user {user.email} with pet {pet.name}")
        return user, pet
```

### Reading Records

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

async def query_examples():
    """Examples of different query patterns."""
    
    async with get_session() as session:
        # Simple query
        stmt = select(User).where(User.email == "owner@example.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        # Query with relationships (eager loading)
        stmt = (
            select(User)
            .options(
                selectinload(User.pets),  # Load pets in separate query
                joinedload(User.veterinarian)  # Load vet profile with JOIN
            )
            .where(User.role == UserRole.PET_OWNER)
        )
        result = await session.execute(stmt)
        users_with_pets = result.unique().scalars().all()
        
        # Complex query with joins and filters
        stmt = (
            select(Pet, User.first_name, User.last_name)
            .join(User, Pet.owner_id == User.id)
            .where(
                and_(
                    Pet.species == PetSpecies.DOG,
                    Pet.weight > 50,
                    User.create_query_filter_active()  # Only active users
                )
            )
            .order_by(Pet.name)
        )
        result = await session.execute(stmt)
        large_dogs = result.all()
        
        return user, users_with_pets, large_dogs
```

### Updating Records

```python
async def update_examples():
    """Examples of updating records."""
    
    async with get_transaction() as session:
        # Update single record
        stmt = select(User).where(User.email == "owner@example.com")
        result = await session.execute(stmt)
        user = result.scalar_one()
        
        # Method 1: Direct attribute assignment
        user.first_name = "Jane"
        user.preferences = {
            **user.preferences,
            "theme": "dark"
        }
        
        # Method 2: Using update_fields helper
        user.update_fields(
            last_name="Smith",
            phone_number="+1-555-0123"
        )
        
        # Bulk update with SQL
        from sqlalchemy import update
        stmt = (
            update(Pet)
            .where(Pet.species == PetSpecies.CAT)
            .values(size=PetSize.SMALL)
        )
        result = await session.execute(stmt)
        print(f"Updated {result.rowcount} cats")
```

### Deleting Records

```python
async def delete_examples():
    """Examples of soft and hard delete."""
    
    async with get_transaction() as session:
        # Soft delete (recommended)
        stmt = select(Pet).where(Pet.name == "Buddy")
        result = await session.execute(stmt)
        pet = result.scalar_one()
        
        pet.soft_delete(deleted_by=current_user_id)
        print(f"Soft deleted pet: {pet.name}")
        
        # Query only active records
        active_pets = await session.execute(
            select(Pet).where(Pet.create_query_filter_active())
        )
        
        # Query deleted records
        deleted_pets = await session.execute(
            select(Pet).where(Pet.create_query_filter_deleted())
        )
        
        # Restore soft-deleted record
        pet.restore(restored_by=current_user_id)
        
        # Hard delete (use with caution)
        await session.delete(pet)
```

## Advanced Patterns

### Batch Operations

```python
async def batch_operations():
    """Efficient batch processing patterns."""
    
    async with get_transaction() as session:
        # Batch insert
        pets_data = [
            {"name": f"Pet_{i}", "species": PetSpecies.DOG, "owner_id": owner_id}
            for i in range(100)
        ]
        
        pets = [Pet(**data) for data in pets_data]
        session.add_all(pets)
        
        # Batch update with SQL
        from sqlalchemy import update
        stmt = (
            update(Pet)
            .where(Pet.species == PetSpecies.DOG)
            .values(size=PetSize.MEDIUM)
        )
        await session.execute(stmt)
        
        # Batch processing with pagination
        page_size = 50
        offset = 0
        
        while True:
            stmt = (
                select(Pet)
                .where(Pet.weight.is_(None))
                .limit(page_size)
                .offset(offset)
            )
            result = await session.execute(stmt)
            pets = result.scalars().all()
            
            if not pets:
                break
                
            # Process batch
            for pet in pets:
                pet.weight = calculate_estimated_weight(pet)
            
            offset += page_size
            
            # Commit periodically for large datasets
            if offset % 500 == 0:
                await session.commit()
```

### Complex Queries with Aggregations

```python
async def analytics_queries():
    """Advanced analytics and reporting queries."""
    
    async with get_session() as session:
        # Appointment statistics by veterinarian
        stmt = (
            select(
                Veterinarian.license_number,
                User.first_name,
                User.last_name,
                func.count(Appointment.id).label('total_appointments'),
                func.avg(Appointment.actual_cost).label('avg_revenue'),
                func.sum(
                    case(
                        (Appointment.status == AppointmentStatus.COMPLETED, 1),
                        else_=0
                    )
                ).label('completed_appointments')
            )
            .select_from(Veterinarian)
            .join(User, Veterinarian.user_id == User.id)
            .outerjoin(Appointment, Appointment.veterinarian_id == Veterinarian.id)
            .where(
                Appointment.scheduled_at >= datetime.now() - timedelta(days=30)
            )
            .group_by(Veterinarian.id, Veterinarian.license_number, User.first_name, User.last_name)
            .order_by(desc('total_appointments'))
        )
        
        result = await session.execute(stmt)
        vet_stats = result.all()
        
        # Pet demographics by clinic
        stmt = (
            select(
                Clinic.name,
                Pet.species,
                func.count(Pet.id).label('pet_count'),
                func.avg(Pet.weight).label('avg_weight')
            )
            .select_from(Pet)
            .join(Appointment, Pet.id == Appointment.pet_id)
            .join(Clinic, Appointment.clinic_id == Clinic.id)
            .group_by(Clinic.id, Clinic.name, Pet.species)
            .order_by(Clinic.name, Pet.species)
        )
        
        result = await session.execute(stmt)
        demographics = result.all()
        
        return vet_stats, demographics
```

### Custom Validation and Business Rules

```python
from vet_core.exceptions import BusinessRuleException, ValidationException

class AppointmentValidator:
    """Custom validator for appointment business rules."""
    
    @staticmethod
    async def validate_appointment_time(
        session, 
        veterinarian_id: str, 
        scheduled_at: datetime,
        duration_minutes: int = 30
    ):
        """Validate appointment doesn't conflict with existing bookings."""
        
        end_time = scheduled_at + timedelta(minutes=duration_minutes)
        
        # Check for conflicts
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.veterinarian_id == veterinarian_id,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
                    ]),
                    or_(
                        # New appointment starts during existing
                        and_(
                            Appointment.scheduled_at <= scheduled_at,
                            Appointment.scheduled_at + 
                            func.interval('1 minute') * Appointment.estimated_duration_minutes > scheduled_at
                        ),
                        # New appointment ends during existing
                        and_(
                            Appointment.scheduled_at < end_time,
                            Appointment.scheduled_at + 
                            func.interval('1 minute') * Appointment.estimated_duration_minutes >= end_time
                        )
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
    
    @staticmethod
    def validate_business_hours(scheduled_at: datetime, clinic_hours: dict):
        """Validate appointment is within business hours."""
        
        day_name = scheduled_at.strftime('%A').lower()
        day_hours = clinic_hours.get(day_name)
        
        if not day_hours or day_hours.get('closed'):
            raise BusinessRuleException(
                f"Clinic is closed on {day_name.title()}",
                rule_name="business_hours_check",
                context={
                    "day": day_name,
                    "requested_time": scheduled_at.isoformat()
                }
            )
        
        appointment_time = scheduled_at.time()
        open_time = datetime.strptime(day_hours['open'], '%H:%M').time()
        close_time = datetime.strptime(day_hours['close'], '%H:%M').time()
        
        if not (open_time <= appointment_time <= close_time):
            raise BusinessRuleException(
                f"Appointment outside business hours ({day_hours['open']}-{day_hours['close']})",
                rule_name="business_hours_check",
                context={
                    "requested_time": appointment_time.isoformat(),
                    "business_hours": day_hours
                }
            )

# Usage
async def create_validated_appointment(appointment_data: AppointmentCreate):
    """Create appointment with full validation."""
    
    async with get_transaction() as session:
        # Get clinic for business hours
        clinic = await session.get(Clinic, appointment_data.clinic_id)
        
        # Validate business rules
        AppointmentValidator.validate_business_hours(
            appointment_data.scheduled_at,
            clinic.operating_hours
        )
        
        await AppointmentValidator.validate_appointment_time(
            session,
            appointment_data.veterinarian_id,
            appointment_data.scheduled_at,
            appointment_data.estimated_duration_minutes
        )
        
        # Create appointment if validation passes
        appointment = Appointment(**appointment_data.model_dump())
        session.add(appointment)
        
        return appointment
```

## Error Handling

### Exception Hierarchy Usage

```python
from vet_core.exceptions import (
    VetCoreException, DatabaseException, ValidationException,
    BusinessRuleException, create_error_response
)

async def robust_operation():
    """Example of comprehensive error handling."""
    
    try:
        # Validate input
        user_data = UserCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.PET_OWNER
        )
        
        # Database operation
        async with get_transaction() as session:
            user = User(**user_data.model_dump())
            session.add(user)
            
    except ValidationException as e:
        # Handle validation errors
        error_response = create_error_response(e, include_debug=True)
        print(f"Validation failed: {e.validation_errors}")
        return {"success": False, "error": error_response}
        
    except BusinessRuleException as e:
        # Handle business rule violations
        print(f"Business rule violated: {e.rule_name}")
        print(f"Context: {e.context}")
        return {"success": False, "error": str(e)}
        
    except DatabaseException as e:
        # Handle database errors with retry logic
        if e.is_retryable():
            print(f"Retryable error, attempt {e.retry_count}/{e.max_retries}")
            # Implement retry logic or let decorator handle it
        else:
            print(f"Non-retryable database error: {e}")
        return {"success": False, "error": "Database operation failed"}
        
    except VetCoreException as e:
        # Handle any other vet-core exceptions
        e.log_error(logger)
        return {"success": False, "error": str(e)}
        
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error: {e}")
        return {"success": False, "error": "Internal server error"}
    
    return {"success": True, "user_id": str(user.id)}
```

### Retry Mechanisms

```python
from vet_core.exceptions import handle_database_retry, execute_with_retry

# Method 1: Decorator
@handle_database_retry("create_user_operation", max_retries=3, base_delay=0.1)
async def create_user_with_retry(user_data: UserCreate):
    """Create user with automatic retry on database errors."""
    async with get_transaction() as session:
        user = User(**user_data.model_dump())
        session.add(user)
        await session.flush()
        return str(user.id)

# Method 2: Function wrapper
async def create_user_manual_retry(user_data: UserCreate):
    """Create user with manual retry logic."""
    
    async def operation(session):
        user = User(**user_data.model_dump())
        session.add(user)
        await session.flush()
        return str(user.id)
    
    return await execute_with_retry(
        operation,
        max_retries=3,
        retry_delay=0.1,
        exponential_backoff=True
    )
```

## Performance Optimization

### Connection Pool Tuning

```python
# For high-traffic applications
engine = create_engine(
    database_url,
    pool_size=20,           # Larger base pool
    max_overflow=50,        # More overflow connections
    pool_timeout=10,        # Shorter timeout
    pool_recycle=1800,      # Recycle every 30 minutes
    pool_pre_ping=True,     # Always validate connections
)

# For low-traffic applications
engine = create_engine(
    database_url,
    pool_size=5,            # Smaller base pool
    max_overflow=10,        # Fewer overflow connections
    pool_timeout=30,        # Longer timeout acceptable
    pool_recycle=3600,      # Recycle every hour
)
```

### Query Optimization

```python
async def optimized_queries():
    """Examples of optimized query patterns."""
    
    async with get_session() as session:
        # Use selectinload for one-to-many relationships
        stmt = (
            select(User)
            .options(selectinload(User.pets))  # Separate query for pets
            .where(User.role == UserRole.PET_OWNER)
        )
        
        # Use joinedload for many-to-one relationships
        stmt = (
            select(Pet)
            .options(joinedload(Pet.owner))  # JOIN with owner
            .where(Pet.species == PetSpecies.DOG)
        )
        
        # Pagination for large result sets
        page_size = 50
        stmt = (
            select(Pet)
            .order_by(Pet.created_at.desc())
            .limit(page_size)
            .offset(page * page_size)
        )
        
        # Use indexes effectively
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.scheduled_at >= start_date,
                    Appointment.scheduled_at <= end_date,
                    Appointment.status == AppointmentStatus.SCHEDULED
                )
            )
            .order_by(Appointment.scheduled_at)  # Use index order
        )
        
        # Aggregate queries for statistics
        stmt = (
            select(
                func.count(Pet.id).label('total_pets'),
                func.count(Pet.id).filter(Pet.species == PetSpecies.DOG).label('dogs'),
                func.avg(Pet.weight).label('avg_weight')
            )
        )
```

### Bulk Operations

```python
async def bulk_operations_optimized():
    """Optimized patterns for bulk operations."""
    
    # Bulk insert with batch processing
    async with get_transaction() as session:
        batch_size = 1000
        pets_data = [...]  # Large list of pet data
        
        for i in range(0, len(pets_data), batch_size):
            batch = pets_data[i:i + batch_size]
            pets = [Pet(**data) for data in batch]
            session.add_all(pets)
            
            # Flush periodically to manage memory
            if i % (batch_size * 10) == 0:
                await session.flush()
    
    # Bulk update with SQL
    async with get_transaction() as session:
        stmt = (
            update(Pet)
            .where(Pet.weight.is_(None))
            .values(weight=func.coalesce(Pet.weight, 0))
        )
        result = await session.execute(stmt)
        print(f"Updated {result.rowcount} records")
```

## Testing

### Test Database Setup

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from vet_core.models import Base

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost/test_vetclinic",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def session(test_engine):
    """Create test session with rollback."""
    from vet_core.database import SessionManager
    
    session_manager = SessionManager(test_engine)
    
    async with session_manager.get_transaction() as session:
        # Use savepoint for test isolation
        savepoint = await session.begin_nested()
        
        yield session
        
        # Rollback to savepoint
        await savepoint.rollback()
```

### Factory Pattern for Test Data

```python
import factory
from datetime import date, datetime
from vet_core.models import User, Pet, UserRole, PetSpecies

class UserFactory(factory.Factory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    clerk_user_id = factory.Sequence(lambda n: f"clerk_user_{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = UserRole.PET_OWNER
    phone_number = factory.Faker('phone_number')

class PetFactory(factory.Factory):
    """Factory for creating test pets."""
    
    class Meta:
        model = Pet
    
    name = factory.Faker('first_name')
    species = PetSpecies.DOG
    breed = factory.Faker('word')
    birth_date = factory.Faker('date_between', start_date=date(2015, 1, 1))
    weight = factory.Faker('pyfloat', left_digits=2, right_digits=1, positive=True)
    owner = factory.SubFactory(UserFactory)

# Usage in tests
async def test_pet_creation(session):
    """Test pet creation with factory."""
    pet = PetFactory()
    session.add(pet)
    await session.flush()
    
    assert pet.id is not None
    assert pet.owner.role == UserRole.PET_OWNER
```

### Integration Tests

```python
async def test_appointment_workflow(session):
    """Test complete appointment workflow."""
    
    # Create test data
    owner = UserFactory(role=UserRole.PET_OWNER)
    vet_user = UserFactory(role=UserRole.VETERINARIAN)
    pet = PetFactory(owner=owner)
    clinic = ClinicFactory()
    veterinarian = VeterinarianFactory(user=vet_user, clinic=clinic)
    
    session.add_all([owner, vet_user, pet, clinic, veterinarian])
    await session.flush()
    
    # Create appointment
    appointment_data = AppointmentCreate(
        pet_id=pet.id,
        veterinarian_id=veterinarian.id,
        clinic_id=clinic.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        service_type=ServiceType.CHECKUP
    )
    
    appointment = Appointment(**appointment_data.model_dump())
    session.add(appointment)
    await session.flush()
    
    # Test appointment lifecycle
    assert appointment.status == AppointmentStatus.SCHEDULED
    
    # Confirm appointment
    appointment.status = AppointmentStatus.CONFIRMED
    
    # Complete appointment
    appointment.status = AppointmentStatus.COMPLETED
    appointment.actual_cost = Decimal("150.00")
    appointment.diagnosis = "Healthy pet, routine checkup"
    
    await session.commit()
    
    # Verify final state
    assert appointment.status == AppointmentStatus.COMPLETED
    assert appointment.actual_cost == Decimal("150.00")
```

## Best Practices

### 1. Always Use Transactions for Write Operations

```python
# Good: Use transaction context manager
async with get_transaction() as session:
    user = User(email="test@example.com")
    session.add(user)
    # Automatically committed

# Avoid: Manual transaction management
async with get_session() as session:
    user = User(email="test@example.com")
    session.add(user)
    await session.commit()  # Manual commit required
```

### 2. Use Pydantic Schemas for Validation

```python
# Good: Validate with Pydantic first
user_data = UserCreate(
    email="test@example.com",
    first_name="John",
    role=UserRole.PET_OWNER
)
user = User(**user_data.model_dump())

# Avoid: Direct model creation without validation
user = User(
    email="invalid-email",  # No validation
    first_name="",          # Empty string allowed
    role="invalid_role"     # Invalid enum value
)
```

### 3. Use Eager Loading to Prevent N+1 Queries

```python
# Good: Eager loading
stmt = (
    select(User)
    .options(selectinload(User.pets))
    .where(User.role == UserRole.PET_OWNER)
)
users = await session.execute(stmt)

# Avoid: Lazy loading in loops
users = await session.execute(select(User))
for user in users.scalars():
    pets = user.pets  # N+1 query problem
```

### 4. Handle Exceptions Appropriately

```python
# Good: Specific exception handling
try:
    user_data = UserCreate(email="test@example.com")
    # ... database operations
except ValidationException as e:
    return {"error": "Invalid input", "details": e.validation_errors}
except DatabaseException as e:
    if e.is_retryable():
        # Retry logic
        pass
    else:
        return {"error": "Database error"}

# Avoid: Generic exception handling
try:
    # ... operations
except Exception as e:
    return {"error": str(e)}  # Loses important context
```

### 5. Use Soft Delete for Data Integrity

```python
# Good: Soft delete preserves relationships
pet.soft_delete(deleted_by=current_user_id)

# Avoid: Hard delete breaks referential integrity
await session.delete(pet)  # May break appointments, etc.
```

### 6. Optimize Database Connections

```python
# Good: Proper connection pool configuration
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)

# Avoid: Default settings for production
engine = create_engine(database_url)  # Uses defaults
```

### 7. Use Type Hints Consistently

```python
# Good: Full type hints
async def create_user(user_data: UserCreate) -> UserResponse:
    async with get_transaction() as session:
        user = User(**user_data.model_dump())
        session.add(user)
        await session.flush()
        return UserResponse.model_validate(user)

# Avoid: Missing type hints
async def create_user(user_data):  # No type information
    # ... implementation
    return user  # Unknown return type
```

### 8. Use Proper Logging

```python
import logging
from vet_core.exceptions import log_exception_context

logger = logging.getLogger(__name__)

# Good: Structured logging with context
try:
    # ... operations
except VetCoreException as e:
    log_exception_context(
        e,
        additional_context={"user_id": current_user_id},
        logger=logger
    )

# Avoid: Generic print statements
except Exception as e:
    print(f"Error: {e}")  # No context or structure
```

This usage guide provides comprehensive coverage of the vet-core package functionality. For more specific examples, refer to the files in the `examples/` directory.