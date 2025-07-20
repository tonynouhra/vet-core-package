"""
Pydantic schemas for data validation and serialization.

This module contains Pydantic schemas for API request/response validation
and data serialization across the veterinary clinic platform.
"""

# Core schemas will be imported as they're implemented
from .user import (
    UserCreate, UserUpdate, UserResponse, UserAdminResponse, UserListResponse,
    UserRoleUpdate, UserStatusUpdate, UserPreferencesUpdate,
    PetOwnerCreate, VeterinarianCreate, VetTechCreate, ClinicAdminCreate
)
# from .pet import PetCreate, PetUpdate, PetResponse
# from .appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
# from .clinic import ClinicCreate, ClinicUpdate, ClinicResponse

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "UserAdminResponse",
    "UserListResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "UserPreferencesUpdate",
    "PetOwnerCreate",
    "VeterinarianCreate",
    "VetTechCreate",
    "ClinicAdminCreate",
    # Pet schemas
    # "PetCreate",
    # "PetUpdate",
    # "PetResponse",
    # Appointment schemas
    # "AppointmentCreate",
    # "AppointmentUpdate",
    # "AppointmentResponse",
    # Clinic schemas
    # "ClinicCreate",
    # "ClinicUpdate",
    # "ClinicResponse",
]