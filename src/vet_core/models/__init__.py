"""
Database models for the vet core package.

This module contains SQLAlchemy models for all core entities in the
veterinary clinic platform.
"""

# Base model will be imported by all other models
from .base import Base, BaseModel

# Core entity models
# These imports will be uncommented as models are implemented
from .user import User, UserRole, UserStatus
# from .pet import Pet
# from .appointment import Appointment
# from .clinic import Clinic
# from .veterinarian import Veterinarian

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserRole",
    "UserStatus",
    # "Pet", 
    # "Appointment",
    # "Clinic",
    # "Veterinarian",
]