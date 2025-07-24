"""
Database models for the vet core package.

This module contains SQLAlchemy models for all core entities in the
veterinary clinic platform.
"""

from .appointment import (
    Appointment,
    AppointmentPriority,
    AppointmentStatus,
    ServiceType,
)

# Base model will be imported by all other models
from .base import Base, BaseModel
from .clinic import Clinic, ClinicStatus, ClinicType
from .pet import Pet, PetGender, PetSize, PetSpecies, PetStatus

# Core entity models
from .user import User, UserRole, UserStatus
from .veterinarian import (
    EmploymentType,
    LicenseStatus,
    Veterinarian,
    VeterinarianStatus,
)

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserRole",
    "UserStatus",
    "Pet",
    "PetSpecies",
    "PetGender",
    "PetSize",
    "PetStatus",
    "Appointment",
    "AppointmentStatus",
    "ServiceType",
    "AppointmentPriority",
    "Clinic",
    "ClinicStatus",
    "ClinicType",
    "Veterinarian",
    "VeterinarianStatus",
    "LicenseStatus",
    "EmploymentType",
]
