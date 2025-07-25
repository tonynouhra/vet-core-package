"""
Pydantic schemas for data validation and serialization.

This module contains Pydantic schemas for API request/response validation
and data serialization across the veterinary clinic platform.
"""

from .appointment import (
    AppointmentCompletion,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentSlotAvailability,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)
from .clinic import (
    ClinicCreate,
    ClinicListResponse,
    ClinicResponse,
    ClinicSearchFilters,
    ClinicStatusUpdate,
    ClinicUpdate,
)
from .pet import (
    PetCreate,
    PetListResponse,
    PetMedicalHistoryUpdate,
    PetResponse,
    PetUpdate,
    PetVaccinationUpdate,
    PetWeightUpdate,
)

# Core schemas will be imported as they're implemented
from .user import (
    ClinicAdminCreate,
    PetOwnerCreate,
    UserAdminResponse,
    UserCreate,
    UserListResponse,
    UserPreferencesUpdate,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
    VetTechCreate,
)
from .veterinarian import (
    VeterinarianAvailabilityUpdate,
    VeterinarianCreate,
    VeterinarianLicenseUpdate,
    VeterinarianListResponse,
    VeterinarianRatingUpdate,
    VeterinarianResponse,
    VeterinarianSearchFilters,
    VeterinarianStatusUpdate,
    VeterinarianUpdate,
)

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
    "PetCreate",
    "PetUpdate",
    "PetResponse",
    "PetListResponse",
    "PetMedicalHistoryUpdate",
    "PetVaccinationUpdate",
    "PetWeightUpdate",
    # Appointment schemas
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse",
    "AppointmentListResponse",
    "AppointmentStatusUpdate",
    "AppointmentReschedule",
    "AppointmentCompletion",
    "AppointmentSlotAvailability",
    # Clinic schemas
    "ClinicCreate",
    "ClinicUpdate",
    "ClinicResponse",
    "ClinicListResponse",
    "ClinicStatusUpdate",
    "ClinicSearchFilters",
    # Veterinarian schemas
    "VeterinarianCreate",
    "VeterinarianUpdate",
    "VeterinarianResponse",
    "VeterinarianListResponse",
    "VeterinarianStatusUpdate",
    "VeterinarianLicenseUpdate",
    "VeterinarianAvailabilityUpdate",
    "VeterinarianSearchFilters",
    "VeterinarianRatingUpdate",
]
