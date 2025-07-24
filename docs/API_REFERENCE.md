# API Reference

This document provides comprehensive API reference for the vet-core package.

## Table of Contents

- [Models](#models)
- [Schemas](#schemas)
- [Database](#database)
- [Utilities](#utilities)
- [Exceptions](#exceptions)

## Models

### Base Model

All models inherit from `BaseModel` which provides common functionality.

```python
from vet_core.models import BaseModel
```

#### BaseModel

**Fields:**
- `id: UUID` - Primary key (automatically generated)
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp
- `created_by: Optional[UUID]` - User who created the record
- `updated_by: Optional[UUID]` - User who last updated the record
- `deleted_at: Optional[datetime]` - Soft delete timestamp
- `is_deleted: bool` - Soft delete flag (default: False)

**Methods:**
- `soft_delete()` - Mark record as deleted
- `restore()` - Restore soft-deleted record
- `to_dict()` - Convert to dictionary
- `refresh_updated_at()` - Update the updated_at timestamp

### User Model

```python
from vet_core.models import User, UserRole, UserStatus
```

#### User

Represents users in the veterinary clinic platform with role-based access control.

**Fields:**
- `clerk_user_id: str` - External authentication provider ID (unique)
- `email: str` - User email address (unique)
- `first_name: str` - User's first name
- `last_name: str` - User's last name
- `phone_number: Optional[str]` - Phone number
- `role: UserRole` - User role (enum)
- `status: UserStatus` - Account status (enum)
- `preferences: Optional[dict]` - User preferences (JSONB)
- `profile_image_url: Optional[str]` - Profile image URL
- `last_login_at: Optional[datetime]` - Last login timestamp

**Relationships:**
- `pets: List[Pet]` - Pets owned by the user (if pet owner)
- `appointments: List[Appointment]` - Appointments booked by the user
- `veterinarian: Optional[Veterinarian]` - Veterinarian profile (if applicable)

**Methods:**
- `get_full_name() -> str` - Returns formatted full name
- `is_pet_owner() -> bool` - Check if user is a pet owner
- `is_veterinarian() -> bool` - Check if user is a veterinarian
- `update_last_login()` - Update last login timestamp

#### UserRole (Enum)

- `PET_OWNER` - Pet owner role
- `VETERINARIAN` - Veterinarian role
- `VET_TECH` - Veterinary technician role
- `CLINIC_ADMIN` - Clinic administrator role
- `PLATFORM_ADMIN` - Platform administrator role

#### UserStatus (Enum)

- `ACTIVE` - Active account
- `INACTIVE` - Inactive account
- `SUSPENDED` - Suspended account
- `PENDING_VERIFICATION` - Pending email verification

### Pet Model

```python
from vet_core.models import Pet, PetSpecies, PetGender, PetSize, PetStatus
```

#### Pet

Represents pets with comprehensive medical and profile information.

**Fields:**
- `owner_id: UUID` - Foreign key to User (owner)
- `name: str` - Pet's name
- `species: PetSpecies` - Pet species (enum)
- `breed: Optional[str]` - Pet breed
- `birth_date: Optional[date]` - Birth date
- `weight: Optional[float]` - Weight in pounds
- `gender: Optional[PetGender]` - Gender (enum)
- `size: Optional[PetSize]` - Size category (enum)
- `color: Optional[str]` - Pet color/markings
- `microchip_id: Optional[str]` - Microchip identification
- `status: PetStatus` - Pet status (enum)
- `medical_history: Optional[dict]` - Medical history (JSONB)
- `notes: Optional[str]` - Additional notes

**Relationships:**
- `owner: User` - Pet owner
- `appointments: List[Appointment]` - Pet's appointments

**Methods:**
- `get_age() -> Optional[int]` - Calculate age in years
- `get_age_months() -> Optional[int]` - Calculate age in months
- `is_senior() -> bool` - Check if pet is considered senior
- `get_vaccination_status() -> dict` - Get vaccination status summary
- `add_medical_record(record: dict)` - Add medical record
- `get_medical_history() -> List[dict]` - Get formatted medical history

#### PetSpecies (Enum)

- `DOG` - Dog
- `CAT` - Cat
- `BIRD` - Bird
- `RABBIT` - Rabbit
- `HAMSTER` - Hamster
- `GUINEA_PIG` - Guinea pig
- `REPTILE` - Reptile
- `FISH` - Fish
- `OTHER` - Other species

#### PetGender (Enum)

- `MALE` - Male
- `FEMALE` - Female
- `MALE_NEUTERED` - Neutered male
- `FEMALE_SPAYED` - Spayed female
- `UNKNOWN` - Unknown gender

#### PetSize (Enum)

- `EXTRA_SMALL` - Extra small (< 10 lbs)
- `SMALL` - Small (10-25 lbs)
- `MEDIUM` - Medium (25-60 lbs)
- `LARGE` - Large (60-90 lbs)
- `EXTRA_LARGE` - Extra large (> 90 lbs)

#### PetStatus (Enum)

- `ACTIVE` - Active pet
- `INACTIVE` - Inactive pet
- `DECEASED` - Deceased pet

### Appointment Model

```python
from vet_core.models import Appointment, AppointmentStatus, ServiceType, AppointmentPriority
```

#### Appointment

Represents scheduled appointments between pets and veterinarians.

**Fields:**
- `pet_id: UUID` - Foreign key to Pet
- `veterinarian_id: UUID` - Foreign key to Veterinarian
- `clinic_id: UUID` - Foreign key to Clinic
- `scheduled_at: datetime` - Appointment date and time
- `status: AppointmentStatus` - Appointment status (enum)
- `service_type: ServiceType` - Type of service (enum)
- `priority: AppointmentPriority` - Priority level (enum)
- `estimated_duration_minutes: int` - Estimated duration
- `actual_duration_minutes: Optional[int]` - Actual duration
- `estimated_cost: Optional[Decimal]` - Estimated cost
- `actual_cost: Optional[Decimal]` - Actual cost
- `notes: Optional[str]` - Appointment notes
- `diagnosis: Optional[str]` - Diagnosis (post-appointment)
- `treatment: Optional[str]` - Treatment provided
- `follow_up_required: bool` - Follow-up required flag
- `follow_up_date: Optional[date]` - Follow-up date

**Relationships:**
- `pet: Pet` - Associated pet
- `veterinarian: Veterinarian` - Assigned veterinarian
- `clinic: Clinic` - Clinic location

**Methods:**
- `is_upcoming() -> bool` - Check if appointment is upcoming
- `is_overdue() -> bool` - Check if appointment is overdue
- `get_duration() -> Optional[int]` - Get actual or estimated duration
- `get_cost() -> Optional[Decimal]` - Get actual or estimated cost
- `can_be_cancelled() -> bool` - Check if appointment can be cancelled
- `can_be_rescheduled() -> bool` - Check if appointment can be rescheduled

#### AppointmentStatus (Enum)

- `SCHEDULED` - Scheduled appointment
- `CONFIRMED` - Confirmed by clinic
- `CHECKED_IN` - Pet checked in
- `IN_PROGRESS` - Appointment in progress
- `COMPLETED` - Appointment completed
- `CANCELLED` - Cancelled appointment
- `NO_SHOW` - Patient didn't show up

#### ServiceType (Enum)

- `CHECKUP` - Regular checkup
- `VACCINATION` - Vaccination appointment
- `SURGERY` - Surgical procedure
- `DENTAL` - Dental care
- `GROOMING` - Grooming service
- `EMERGENCY` - Emergency visit
- `FOLLOW_UP` - Follow-up appointment
- `CONSULTATION` - Consultation only

#### AppointmentPriority (Enum)

- `LOW` - Low priority
- `NORMAL` - Normal priority
- `HIGH` - High priority
- `URGENT` - Urgent priority
- `EMERGENCY` - Emergency priority

### Clinic Model

```python
from vet_core.models import Clinic, ClinicStatus, ClinicType
```

#### Clinic

Represents veterinary clinics with location and service information.

**Fields:**
- `name: str` - Clinic name
- `address: str` - Physical address
- `phone_number: str` - Primary phone number
- `email: Optional[str]` - Contact email
- `website: Optional[str]` - Website URL
- `status: ClinicStatus` - Clinic status (enum)
- `clinic_type: ClinicType` - Type of clinic (enum)
- `operating_hours: Optional[dict]` - Operating hours (JSONB)
- `services_offered: Optional[List[str]]` - List of services
- `location: Optional[dict]` - GPS coordinates (JSONB)
- `license_number: Optional[str]` - Clinic license number
- `emergency_services: bool` - Emergency services available
- `rating: Optional[Decimal]` - Average rating

**Relationships:**
- `veterinarians: List[Veterinarian]` - Veterinarians at clinic
- `appointments: List[Appointment]` - Appointments at clinic

**Methods:**
- `is_open_now() -> bool` - Check if clinic is currently open
- `get_next_opening() -> Optional[datetime]` - Get next opening time
- `is_emergency_available() -> bool` - Check emergency availability
- `get_distance_from(lat: float, lng: float) -> Optional[float]` - Calculate distance
- `get_available_services() -> List[str]` - Get list of services

#### ClinicStatus (Enum)

- `ACTIVE` - Active clinic
- `INACTIVE` - Inactive clinic
- `TEMPORARILY_CLOSED` - Temporarily closed
- `PERMANENTLY_CLOSED` - Permanently closed

#### ClinicType (Enum)

- `GENERAL_PRACTICE` - General veterinary practice
- `SPECIALTY` - Specialty clinic
- `EMERGENCY` - Emergency clinic
- `MOBILE` - Mobile veterinary service
- `HOSPITAL` - Veterinary hospital

### Veterinarian Model

```python
from vet_core.models import Veterinarian, VeterinarianStatus, LicenseStatus, EmploymentType
```

#### Veterinarian

Represents veterinarian profiles with credentials and specializations.

**Fields:**
- `user_id: UUID` - Foreign key to User
- `clinic_id: UUID` - Foreign key to Clinic
- `license_number: str` - Professional license number
- `status: VeterinarianStatus` - Status (enum)
- `license_status: LicenseStatus` - License status (enum)
- `employment_type: EmploymentType` - Employment type (enum)
- `specializations: Optional[List[str]]` - Areas of specialization
- `education: Optional[dict]` - Education history (JSONB)
- `experience_years: Optional[int]` - Years of experience
- `availability: Optional[dict]` - Availability schedule (JSONB)
- `rating: Optional[Decimal]` - Average rating
- `bio: Optional[str]` - Professional biography

**Relationships:**
- `user: User` - Associated user account
- `clinic: Clinic` - Primary clinic
- `appointments: List[Appointment]` - Assigned appointments

**Methods:**
- `is_available_at(datetime) -> bool` - Check availability
- `get_next_available_slot() -> Optional[datetime]` - Get next available time
- `get_specialization_list() -> List[str]` - Get formatted specializations
- `calculate_rating() -> Decimal` - Calculate current rating
- `is_licensed() -> bool` - Check if currently licensed

#### VeterinarianStatus (Enum)

- `ACTIVE` - Active veterinarian
- `INACTIVE` - Inactive veterinarian
- `ON_LEAVE` - On leave
- `SUSPENDED` - Suspended

#### LicenseStatus (Enum)

- `VALID` - Valid license
- `EXPIRED` - Expired license
- `SUSPENDED` - Suspended license
- `REVOKED` - Revoked license
- `PENDING` - Pending renewal

#### EmploymentType (Enum)

- `FULL_TIME` - Full-time employee
- `PART_TIME` - Part-time employee
- `CONTRACT` - Contract worker
- `LOCUM` - Locum tenens

## Schemas

### User Schemas

```python
from vet_core.schemas import (
    UserCreate, UserUpdate, UserResponse, UserAdminResponse,
    UserListResponse, UserRoleUpdate, UserStatusUpdate
)
```

#### UserCreate

Schema for creating new users.

**Fields:**
- `clerk_user_id: str` - External auth ID (required)
- `email: EmailStr` - Email address (required)
- `first_name: str` - First name (required)
- `last_name: str` - Last name (required)
- `phone_number: Optional[str]` - Phone number
- `role: UserRole` - User role (required)
- `preferences: Optional[dict]` - User preferences

#### UserUpdate

Schema for updating existing users.

**Fields:**
- `first_name: Optional[str]` - First name
- `last_name: Optional[str]` - Last name
- `phone_number: Optional[str]` - Phone number
- `preferences: Optional[dict]` - User preferences
- `profile_image_url: Optional[str]` - Profile image URL

#### UserResponse

Schema for user responses (excludes sensitive data).

**Fields:**
- `id: UUID` - User ID
- `email: str` - Email address
- `first_name: str` - First name
- `last_name: str` - Last name
- `role: UserRole` - User role
- `status: UserStatus` - Account status
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Update timestamp

### Pet Schemas

```python
from vet_core.schemas import (
    PetCreate, PetUpdate, PetResponse, PetListResponse,
    PetMedicalHistoryUpdate, PetVaccinationUpdate
)
```

#### PetCreate

Schema for creating new pets.

**Fields:**
- `owner_id: UUID` - Owner user ID (required)
- `name: str` - Pet name (required)
- `species: PetSpecies` - Pet species (required)
- `breed: Optional[str]` - Pet breed
- `birth_date: Optional[date]` - Birth date
- `weight: Optional[float]` - Weight in pounds
- `gender: Optional[PetGender]` - Gender
- `color: Optional[str]` - Color/markings
- `microchip_id: Optional[str]` - Microchip ID
- `medical_history: Optional[dict]` - Medical history

#### PetResponse

Schema for pet responses.

**Fields:**
- `id: UUID` - Pet ID
- `name: str` - Pet name
- `species: PetSpecies` - Pet species
- `breed: Optional[str]` - Pet breed
- `age_years: Optional[int]` - Calculated age in years
- `weight: Optional[float]` - Weight
- `owner: UserResponse` - Owner information
- `created_at: datetime` - Creation timestamp

### Appointment Schemas

```python
from vet_core.schemas import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse,
    AppointmentStatusUpdate, AppointmentReschedule
)
```

#### AppointmentCreate

Schema for creating appointments.

**Fields:**
- `pet_id: UUID` - Pet ID (required)
- `veterinarian_id: UUID` - Veterinarian ID (required)
- `clinic_id: UUID` - Clinic ID (required)
- `scheduled_at: datetime` - Appointment time (required)
- `service_type: ServiceType` - Service type (required)
- `estimated_duration_minutes: int` - Duration (default: 30)
- `notes: Optional[str]` - Appointment notes

#### AppointmentResponse

Schema for appointment responses.

**Fields:**
- `id: UUID` - Appointment ID
- `scheduled_at: datetime` - Appointment time
- `status: AppointmentStatus` - Current status
- `service_type: ServiceType` - Service type
- `pet: PetResponse` - Pet information
- `veterinarian: VeterinarianResponse` - Veterinarian info
- `clinic: ClinicResponse` - Clinic information
- `estimated_cost: Optional[Decimal]` - Estimated cost

## Database

### Connection Management

```python
from vet_core.database import create_engine, get_session, get_transaction
```

#### create_engine

Create a configured SQLAlchemy async engine.

```python
engine = create_engine(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
    echo: bool = False
)
```

#### get_session

Get an async database session.

```python
async with get_session() as session:
    # Read operations
    result = await session.execute(select(User))
    users = result.scalars().all()
```

#### get_transaction

Get an async database session with automatic transaction management.

```python
async with get_transaction() as session:
    # Write operations - automatically committed
    user = User(email="test@example.com")
    session.add(user)
    # Automatic commit on success, rollback on error
```

### Session Management

```python
from vet_core.database import SessionManager, health_check, get_pool_status
```

#### health_check

Perform database health check.

```python
health_status = await health_check(force=True)
# Returns: {"status": "healthy", "checks": {...}, "pool_info": {...}}
```

#### get_pool_status

Get connection pool status information.

```python
pool_status = await get_pool_status()
# Returns: {"pool_class": "...", "size": 10, "checked_out": 2, ...}
```

### Retry Mechanisms

```python
from vet_core.database import execute_with_retry
```

#### execute_with_retry

Execute database operation with retry logic.

```python
async def my_operation(session):
    # Database operation that might fail
    return await session.execute(select(User))

result = await execute_with_retry(
    my_operation,
    max_retries=3,
    retry_delay=0.1,
    exponential_backoff=True
)
```

## Utilities

### DateTime Utilities

```python
from vet_core.utils.datetime_utils import (
    now_utc, to_timezone, calculate_age, is_business_hours
)
```

#### now_utc

Get current UTC datetime.

```python
current_time = now_utc()
```

#### to_timezone

Convert datetime to specific timezone.

```python
local_time = to_timezone(utc_time, "America/New_York")
```

#### calculate_age

Calculate age from birth date.

```python
age_years = calculate_age(birth_date)
age_months = calculate_age(birth_date, unit="months")
```

#### is_business_hours

Check if datetime falls within business hours.

```python
is_open = is_business_hours(
    datetime_obj,
    business_hours={"monday": {"open": "09:00", "close": "17:00"}}
)
```

### Validation Utilities

```python
from vet_core.utils.validation import (
    validate_email, validate_phone, sanitize_input
)
```

#### validate_email

Validate email address format.

```python
is_valid = validate_email("user@example.com")
```

#### validate_phone

Validate and format phone number.

```python
formatted_phone = validate_phone("+1-555-123-4567")
```

#### sanitize_input

Sanitize user input for security.

```python
clean_input = sanitize_input(user_input)
```

### Configuration Utilities

```python
from vet_core.utils.config import get_database_url, get_setting
```

#### get_database_url

Get database URL from environment.

```python
db_url = get_database_url(default="postgresql://localhost/vetdb")
```

#### get_setting

Get configuration setting with type conversion.

```python
pool_size = get_setting("DB_POOL_SIZE", default=10, type_=int)
debug_mode = get_setting("DEBUG", default=False, type_=bool)
```

## Exceptions

### Exception Hierarchy

```python
from vet_core.exceptions import (
    VetCoreException, DatabaseException, ValidationException,
    BusinessRuleException, ConfigurationException
)
```

#### VetCoreException

Base exception for all vet-core errors.

**Attributes:**
- `message: str` - Error message
- `error_code: str` - Error code
- `details: dict` - Additional details
- `timestamp: datetime` - Error timestamp

**Methods:**
- `log_error(logger)` - Log error with context
- `get_debug_info() -> dict` - Get debug information
- `to_dict() -> dict` - Convert to dictionary

#### DatabaseException

Database-related errors with retry support.

**Additional Attributes:**
- `retry_count: int` - Current retry count
- `max_retries: int` - Maximum retries allowed
- `original_error: Optional[Exception]` - Original exception

**Methods:**
- `is_retryable() -> bool` - Check if error is retryable
- `get_retry_delay() -> float` - Get retry delay
- `increment_retry() -> DatabaseException` - Create retry instance

#### ValidationException

Data validation errors.

**Additional Attributes:**
- `field: Optional[str]` - Field that failed validation
- `value: Any` - Invalid value
- `validation_errors: dict` - Detailed validation errors

#### BusinessRuleException

Business rule violations.

**Additional Attributes:**
- `rule_name: str` - Name of violated rule
- `context: dict` - Rule context information

#### ConfigurationException

Configuration and environment errors.

**Additional Attributes:**
- `config_key: str` - Configuration key
- `config_value: Any` - Configuration value (sanitized)

### Error Handling Utilities

```python
from vet_core.exceptions import (
    create_error_response, format_validation_errors,
    handle_database_retry, log_exception_context
)
```

#### create_error_response

Create standardized error response.

```python
error_response = create_error_response(
    exception,
    include_debug=False,
    request_id="req_123"
)
```

#### format_validation_errors

Format Pydantic validation errors.

```python
formatted_errors = format_validation_errors(pydantic_errors)
```

#### handle_database_retry

Decorator for automatic database retry.

```python
@handle_database_retry("operation_name", max_retries=3)
async def my_database_operation():
    # Database operation
    pass
```

#### log_exception_context

Log exception with additional context.

```python
log_exception_context(
    exception,
    additional_context={"user_id": "123"},
    logger=my_logger
)
```

---

This API reference covers the core functionality of the vet-core package. For more detailed examples and usage patterns, see the [examples directory](../examples/) and the main [README](../README.md).