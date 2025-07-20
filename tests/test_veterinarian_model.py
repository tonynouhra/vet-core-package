"""
Tests for the Veterinarian model.

This module contains unit tests for the Veterinarian SQLAlchemy model,
testing model creation, properties, and business logic.
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.vet_core.models.veterinarian import (
    Veterinarian, VeterinarianStatus, LicenseStatus, EmploymentType
)


class TestVeterinarianModel:
    """Test cases for the Veterinarian model."""
    
    def test_veterinarian_creation(self):
        """Test basic veterinarian creation with required fields."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        assert vet.user_id == user_id
        assert vet.clinic_id == clinic_id
        assert vet.license_number == "VET123456"
        assert vet.license_state == "CA"
        assert vet.license_country == "US"
        assert vet.status == VeterinarianStatus.ACTIVE  # Default status
        assert vet.license_status == LicenseStatus.ACTIVE  # Default status
        assert vet.employment_type == EmploymentType.FULL_TIME  # Default type
        assert vet.is_accepting_new_patients is True  # Default value
        assert vet.years_of_experience == 0  # Default value
        assert vet.rating == Decimal('0.0')  # Default value
        assert vet.total_reviews == 0  # Default value
    
    def test_veterinarian_properties(self):
        """Test veterinarian properties."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test is_active property
        assert vet.is_active is True
        vet.status = VeterinarianStatus.INACTIVE
        assert vet.is_active is False
        
        # Test is_available_for_appointments property
        vet.status = VeterinarianStatus.ACTIVE
        assert vet.is_available_for_appointments is True
        vet.is_accepting_new_patients = False
        assert vet.is_available_for_appointments is False
        
        # Test license_is_valid property
        vet.is_accepting_new_patients = True
        assert vet.license_is_valid is True
        vet.license_status = LicenseStatus.EXPIRED
        assert vet.license_is_valid is False
    
    def test_license_expiry(self):
        """Test license expiry functionality."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test without expiry date
        assert vet.license_is_valid is True
        assert vet.license_expires_soon is False
        
        # Test with future expiry date
        future_date = date.today() + timedelta(days=60)
        vet.license_expiry_date = future_date
        assert vet.license_is_valid is True
        assert vet.license_expires_soon is False
        
        # Test with expiry date within 30 days
        soon_date = date.today() + timedelta(days=15)
        vet.license_expiry_date = soon_date
        assert vet.license_is_valid is True
        assert vet.license_expires_soon is True
        
        # Test with past expiry date
        past_date = date.today() - timedelta(days=1)
        vet.license_expiry_date = past_date
        assert vet.license_is_valid is False
        assert vet.license_expires_soon is True
    
    def test_specializations(self):
        """Test specialization management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test initial state
        assert vet.has_specialization("Internal Medicine") is False
        
        # Test adding specializations
        vet.add_specialization("Internal Medicine")
        vet.add_specialization("Surgery")
        assert vet.has_specialization("Internal Medicine") is True
        assert vet.has_specialization("Surgery") is True
        assert vet.has_specialization("Cardiology") is False
        
        # Test removing specializations
        vet.remove_specialization("Surgery")
        assert vet.has_specialization("Surgery") is False
        
        # Test adding duplicate specialization
        vet.add_specialization("Internal Medicine")  # Should not duplicate
        assert vet.specializations.count("Internal Medicine") == 1
    
    def test_services(self):
        """Test service management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test adding services
        vet.add_service("Wellness Exams")
        vet.add_service("Emergency Care")
        assert vet.provides_service("Wellness Exams") is True
        assert vet.provides_service("Emergency Care") is True
        assert vet.provides_service("Surgery") is False
    
    def test_species_expertise(self):
        """Test species expertise management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test adding species expertise
        vet.add_species_expertise("Dogs")
        vet.add_species_expertise("Cats")
        assert vet.has_species_expertise("Dogs") is True
        assert vet.has_species_expertise("Cats") is True
        assert vet.has_species_expertise("Birds") is False
    
    def test_availability(self):
        """Test availability management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test initial state
        assert vet.is_available_on_day("monday") is False
        assert vet.get_availability_for_day("monday") is None
        
        # Test setting availability
        vet.set_availability("monday", "09:00", "17:00")
        assert vet.is_available_on_day("monday") is True
        
        availability = vet.get_availability_for_day("monday")
        assert availability is not None
        assert availability["is_available"] is True
        assert availability["start_time"] == "09:00"
        assert availability["end_time"] == "17:00"
        
        # Test with break times
        break_times = [{"start": "12:00", "end": "13:00"}]
        vet.set_availability("tuesday", "08:00", "18:00", break_times=break_times)
        
        availability = vet.get_availability_for_day("tuesday")
        assert availability["breaks"] == break_times
        
        # Test unavailable day
        vet.set_availability("sunday", "00:00", "00:00", is_available=False)
        assert vet.is_available_on_day("sunday") is False
    
    def test_rating_management(self):
        """Test rating and review management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test initial state
        assert vet.rating == Decimal('0.0')
        assert vet.total_reviews == 0
        assert vet.rating_display == "No reviews yet"
        
        # Test first review
        vet.update_rating(Decimal('4.5'))
        assert vet.rating == Decimal('4.5')
        assert vet.total_reviews == 1
        assert "4.5/5.0 (1 review)" in vet.rating_display
        
        # Test second review
        vet.update_rating(Decimal('5.0'))
        assert vet.rating == Decimal('4.75')  # Average of 4.5 and 5.0
        assert vet.total_reviews == 2
        assert "4.8/5.0 (2 reviews)" in vet.rating_display
        
        # Test invalid rating
        try:
            vet.update_rating(Decimal('6.0'))  # Invalid rating
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
    
    def test_certification_management(self):
        """Test certification management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test adding certification
        cert_date = date(2020, 6, 15)
        expiry_date = date(2030, 6, 15)
        
        vet.add_certification(
            "Board Certified Internal Medicine",
            "American College of Veterinary Internal Medicine",
            cert_date,
            expiry_date,
            "ACVIM-12345"
        )
        
        assert vet.has_certification("Board Certified Internal Medicine") is True
        assert vet.has_certification("Board Certified Surgery") is False
        
        # Test certification without expiry
        vet.add_certification(
            "CPR Certified",
            "Veterinary CPR Association",
            cert_date
        )
        
        assert vet.has_certification("CPR Certified") is True
        
        # Test expired certification
        expired_date = date(2020, 1, 1)
        vet.add_certification(
            "Expired Cert",
            "Test Organization",
            cert_date,
            expired_date
        )
        
        assert vet.has_certification("Expired Cert") is False
        
        # Test expiring certifications
        expiring_date = date.today() + timedelta(days=15)
        vet.add_certification(
            "Expiring Soon",
            "Test Organization",
            cert_date,
            expiring_date
        )
        
        expiring_certs = vet.get_expiring_certifications(30)
        assert len(expiring_certs) >= 1
        assert any(cert["name"] == "Expiring Soon" for cert in expiring_certs)
    
    def test_license_management(self):
        """Test license status management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test license status update
        vet.update_license_status(LicenseStatus.EXPIRED, "License expired")
        assert vet.license_status == LicenseStatus.EXPIRED
        assert vet.status == VeterinarianStatus.SUSPENDED
        assert vet.is_accepting_new_patients is False
        assert "License expired" in vet.bio
        
        # Test license renewal
        future_date = date.today() + timedelta(days=365)
        vet.renew_license(future_date)
        assert vet.license_status == LicenseStatus.ACTIVE
        assert vet.license_expiry_date == future_date
        assert vet.status == VeterinarianStatus.ACTIVE
    
    def test_status_management(self):
        """Test veterinarian status management."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        # Test suspension
        vet.suspend("Disciplinary action")
        assert vet.status == VeterinarianStatus.SUSPENDED
        assert vet.is_accepting_new_patients is False
        assert "Suspended: Disciplinary action" in vet.bio
        
        # Test reactivation
        vet.reactivate("Issue resolved")
        assert vet.status == VeterinarianStatus.ACTIVE
        assert vet.is_accepting_new_patients is True
        assert "Reactivated: Issue resolved" in vet.bio
        
        # Test reactivation with invalid license
        vet.license_status = LicenseStatus.EXPIRED
        try:
            vet.reactivate("Trying to reactivate")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
        
        # Test retirement
        retirement_date = date.today()
        vet.license_status = LicenseStatus.ACTIVE  # Reset license
        vet.retire(retirement_date)
        assert vet.status == VeterinarianStatus.RETIRED
        assert vet.is_accepting_new_patients is False
        assert retirement_date.isoformat() in vet.bio
    
    def test_capacity_management(self):
        """Test capacity utilization functionality."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US",
            max_daily_appointments=20
        )
        
        # Test capacity utilization
        utilization = vet.calculate_capacity_utilization(10)
        assert utilization == 50.0
        
        utilization = vet.calculate_capacity_utilization(20)
        assert utilization == 100.0
        
        utilization = vet.calculate_capacity_utilization(25)
        assert utilization == 100.0  # Capped at 100%
        
        # Test at capacity
        assert vet.is_at_capacity(10) is False
        assert vet.is_at_capacity(20) is True
        assert vet.is_at_capacity(25) is True
        
        # Test without max capacity set
        vet.max_daily_appointments = None
        assert vet.calculate_capacity_utilization(10) is None
        assert vet.is_at_capacity(10) is False
    
    def test_credentials_display(self):
        """Test credentials display functionality."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US",
            degree_type="DVM"
        )
        
        # Test with degree only
        assert vet.full_credentials == "DVM"
        
        # Test with specializations
        vet.add_specialization("Internal Medicine")
        vet.add_specialization("Surgery")
        credentials = vet.full_credentials
        assert "DVM" in credentials
        assert "Internal Medicine" in credentials
        assert "Surgery" in credentials
        
        # Test without degree
        vet.degree_type = None
        assert vet.full_credentials == "Internal Medicine, Surgery"
    
    def test_display_methods(self):
        """Test display methods."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US",
            status=VeterinarianStatus.ACTIVE,
            license_status=LicenseStatus.ACTIVE,
            employment_type=EmploymentType.FULL_TIME
        )
        
        # Test status display
        assert vet.get_status_display() == "Active"
        vet.status = VeterinarianStatus.ON_LEAVE
        assert vet.get_status_display() == "On Leave"
        
        # Test license status display
        assert vet.get_license_status_display() == "Active"
        vet.license_status = LicenseStatus.PENDING_RENEWAL
        assert vet.get_license_status_display() == "Pending Renewal"
        
        # Test employment type display
        assert vet.get_employment_type_display() == "Full Time"
        vet.employment_type = EmploymentType.PART_TIME
        assert vet.get_employment_type_display() == "Part Time"
    
    def test_repr(self):
        """Test string representation."""
        user_id = uuid.uuid4()
        clinic_id = uuid.uuid4()
        
        vet = Veterinarian(
            user_id=user_id,
            clinic_id=clinic_id,
            license_number="VET123456",
            license_state="CA",
            license_country="US"
        )
        
        repr_str = repr(vet)
        assert str(user_id) in repr_str
        assert "VET123456" in repr_str
        assert "active" in repr_str