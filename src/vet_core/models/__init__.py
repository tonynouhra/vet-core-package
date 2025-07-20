"""
Database models for the vet core package.

This module contains SQLAlchemy models for all core entities in the
veterinary clinic platform.
"""

# Base model will be imported by all other models
from .base import Base, BaseModel

# Core entity models
from .user import User, UserRole, UserStatus
from .pet import Pet, PetSpecies, PetGender, PetSize, PetStatus
from .appointment import Appointment, AppointmentStatus, ServiceType, AppointmentPriority
from .clinic import Clinic, ClinicStatus, ClinicType
from .veterinarian import Veterinarian, VeterinarianStatus, LicenseStatus, EmploymentType

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