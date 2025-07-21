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
from .pet import (
    PetCreate, PetUpdate, PetResponse, PetListResponse,
    PetMedicalHistoryUpdate, PetVaccinationUpdate, PetWeightUpdate
)
from .appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentListResponse,
    AppointmentStatusUpdate, AppointmentReschedule, AppointmentCompletion,
    AppointmentSlotAvailability
)
from .clinic import (
    ClinicCreate, ClinicUpdate, ClinicResponse, ClinicListResponse,
    ClinicStatusUpdate, ClinicSearchFilters
)
from .veterinarian import (
    VeterinarianCreate, VeterinarianUpdate, VeterinarianResponse, VeterinarianListResponse,
    VeterinarianStatusUpdate, VeterinarianLicenseUpdate, VeterinarianAvailabilityUpdate,
    VeterinarianSearchFilters, VeterinarianRatingUpdate
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