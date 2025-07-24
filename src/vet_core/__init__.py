"""
Vet Core Package

A foundational Python package providing shared data models, database utilities,
and validation schemas for the veterinary clinic platform.

This package serves as the single source of truth for data structures across
the distributed veterinary clinic platform. It includes:

- SQLAlchemy models for core entities (Users, Pets, Appointments, Clinics, Veterinarians)
- Pydantic schemas for request/response validation and serialization
- Database connection utilities with async SQLAlchemy engine configuration
- Helper functions for common operations like datetime handling and validation
- Comprehensive exception handling with retry mechanisms
- Migration support through Alembic integration
- Testing utilities and factory classes for development

Quick Start:
    >>> from vet_core.models import User, Pet, Appointment
    >>> from vet_core.database import get_session
    >>> from vet_core.schemas import UserCreate, PetCreate
    
    >>> # Create a new user
    >>> user_data = UserCreate(
    ...     email="owner@example.com",
    ...     first_name="John",
    ...     last_name="Doe",
    ...     role="pet_owner"
    ... )
    
    >>> # Use async session for database operations
    >>> async with get_session() as session:
    ...     user = User(**user_data.model_dump())
    ...     session.add(user)
    ...     await session.commit()

Requirements:
    - Python 3.11+
    - PostgreSQL 13+
    - SQLAlchemy 2.0+
    - Pydantic 2.5+

For more information, see the documentation at:
https://vet-core.readthedocs.io/
"""

__version__ = "0.1.0"
__author__ = "Vet Clinic Platform Team"
__email__ = "dev@vetclinic.com"
__license__ = "MIT"
__copyright__ = "Copyright 2025 Vet Clinic Platform Team"

# Import implemented modules
from . import database
from . import exceptions
from . import models
from . import schemas
from . import utils

# Convenience imports for common usage patterns
from .database import get_session, get_transaction, create_engine
from .exceptions import VetCoreException, ValidationException, DatabaseException
from .models import User, Pet, Appointment, Clinic, Veterinarian

__all__ = [
    # Version and metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__copyright__",
    
    # Core modules
    "database",
    "exceptions", 
    "models",
    "schemas",
    "utils",
    
    # Convenience imports
    "get_session",
    "get_transaction", 
    "create_engine",
    "VetCoreException",
    "ValidationException",
    "DatabaseException",
    "User",
    "Pet",
    "Appointment",
    "Clinic",
    "Veterinarian",
]