"""
Tests for the Clinic model.

This module contains unit tests for the Clinic SQLAlchemy model,
testing model creation, properties, and business logic.
"""

import uuid
from datetime import datetime

import pytest

from src.vet_core.models.clinic import Clinic, ClinicStatus, ClinicType


class TestClinicModel:
    """Test cases for the Clinic model."""

    def test_clinic_creation(self):
        """Test basic clinic creation with required fields."""
        clinic = Clinic(
            name="Happy Paws Veterinary Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        assert clinic.name == "Happy Paws Veterinary Clinic"
        assert clinic.phone_number == "555-123-4567"
        assert clinic.address_line1 == "123 Main Street"
        assert clinic.city == "Anytown"
        assert clinic.state == "CA"
        assert clinic.postal_code == "12345"
        assert clinic.status == ClinicStatus.ACTIVE  # Default status
        assert clinic.type == ClinicType.GENERAL_PRACTICE  # Default type
        assert clinic.accepts_new_patients is True  # Default value
        assert clinic.accepts_emergencies is False  # Default value
        assert clinic.accepts_walk_ins is False  # Default value
        assert clinic.country == "US"  # Default value

    def test_clinic_properties(self):
        """Test clinic properties."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test is_active property
        assert clinic.is_active is True
        clinic.status = ClinicStatus.INACTIVE
        assert clinic.is_active is False

        # Test is_open_for_business property
        clinic.status = ClinicStatus.ACTIVE
        assert clinic.is_open_for_business is True
        clinic.accepts_new_patients = False
        assert clinic.is_open_for_business is False

        # Test display_name property
        assert clinic.display_name == "Test Clinic"

    def test_full_address_property(self):
        """Test the full_address property."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        expected_address = "123 Main Street, Anytown, CA, 12345"
        assert clinic.full_address == expected_address

        # Test with address_line2
        clinic.address_line2 = "Suite 100"
        expected_address = "123 Main Street, Suite 100, Anytown, CA, 12345"
        assert clinic.full_address == expected_address

        # Test with non-US country
        clinic.country = "CA"  # Canada
        expected_address = "123 Main Street, Suite 100, Anytown, CA, 12345, CA"
        assert clinic.full_address == expected_address

    def test_coordinates(self):
        """Test coordinate handling."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test initial state
        assert clinic.has_coordinates is False
        assert clinic.coordinates is None

        # Test setting coordinates
        clinic.set_coordinates(37.7749, -122.4194)
        assert clinic.has_coordinates is True
        assert clinic.coordinates == (37.7749, -122.4194)
        assert clinic.latitude == 37.7749
        assert clinic.longitude == -122.4194

        # Test invalid coordinates
        try:
            clinic.set_coordinates(91.0, 0.0)  # Invalid latitude
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        try:
            clinic.set_coordinates(0.0, 181.0)  # Invalid longitude
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

    def test_operating_hours(self):
        """Test operating hours functionality."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test initial state
        assert clinic.is_open_on_day("monday") is False
        assert clinic.get_hours_for_day("monday") is None

        # Test setting operating hours
        clinic.set_operating_hours("monday", "08:00", "18:00")
        assert clinic.is_open_on_day("monday") is True

        hours = clinic.get_hours_for_day("monday")
        assert hours is not None
        assert hours["is_open"] is True
        assert hours["open_time"] == "08:00"
        assert hours["close_time"] == "18:00"

        # Test with lunch break
        lunch_break = {"start": "12:00", "end": "13:00"}
        clinic.set_operating_hours("tuesday", "09:00", "17:00", lunch_break=lunch_break)

        hours = clinic.get_hours_for_day("tuesday")
        assert hours["lunch_break"] == lunch_break

        # Test closed day
        clinic.set_operating_hours("sunday", "00:00", "00:00", is_open=False)
        assert clinic.is_open_on_day("sunday") is False

    def test_services(self):
        """Test service management."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test initial state
        assert clinic.has_service("Wellness Exams") is False

        # Test adding services
        clinic.add_service("Wellness Exams")
        clinic.add_service("Vaccinations")
        assert clinic.has_service("Wellness Exams") is True
        assert clinic.has_service("Vaccinations") is True
        assert clinic.has_service("Surgery") is False

        # Test removing services
        clinic.remove_service("Vaccinations")
        assert clinic.has_service("Vaccinations") is False

        # Test adding duplicate service
        clinic.add_service("Wellness Exams")  # Should not duplicate
        assert clinic.services_offered.count("Wellness Exams") == 1

    def test_specialties(self):
        """Test specialty management."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test adding specialties
        clinic.add_specialty("Internal Medicine")
        clinic.add_specialty("Surgery")
        assert clinic.has_specialty("Internal Medicine") is True
        assert clinic.has_specialty("Surgery") is True
        assert clinic.has_specialty("Cardiology") is False

        # Test removing specialties
        clinic.remove_specialty("Surgery")
        assert clinic.has_specialty("Surgery") is False

    def test_facility_features(self):
        """Test facility feature management."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test adding features
        clinic.add_facility_feature("parking")
        clinic.add_facility_feature("wheelchair_accessible")
        assert clinic.has_facility_feature("parking") is True
        assert clinic.has_facility_feature("wheelchair_accessible") is True
        assert clinic.has_facility_feature("24_hour") is False

    def test_insurance_and_payment(self):
        """Test insurance and payment method checking."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
            insurance_accepted=["Pet Insurance Co", "VetCare"],
            payment_methods=["cash", "credit_card", "check"],
        )

        # Test insurance acceptance
        assert clinic.accepts_insurance("Pet Insurance Co") is True
        assert clinic.accepts_insurance("Other Insurance") is False

        # Test payment methods
        assert clinic.accepts_payment_method("credit_card") is True
        assert clinic.accepts_payment_method("bitcoin") is False

    def test_status_management(self):
        """Test clinic status management."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        # Test status updates
        clinic.update_status(ClinicStatus.TEMPORARILY_CLOSED, "Renovation")
        assert clinic.status == ClinicStatus.TEMPORARILY_CLOSED
        assert "Renovation" in clinic.description

        # Test temporary closure
        clinic.temporarily_close("Staff shortage")
        assert clinic.status == ClinicStatus.TEMPORARILY_CLOSED
        assert clinic.accepts_new_patients is False

        # Test reopening
        clinic.reopen("Fully staffed")
        assert clinic.status == ClinicStatus.ACTIVE
        assert clinic.accepts_new_patients is True

        # Test permanent closure
        clinic.permanently_close("Business closure")
        assert clinic.status == ClinicStatus.PERMANENTLY_CLOSED
        assert clinic.accepts_new_patients is False
        assert clinic.accepts_emergencies is False
        assert clinic.accepts_walk_ins is False

    def test_distance_calculation(self):
        """Test distance calculation functionality."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="San Francisco",
            state="CA",
            postal_code="94102",
        )

        # Test without coordinates
        distance = clinic.calculate_distance_to(37.7749, -122.4194)
        assert distance is None

        # Test with coordinates
        clinic.set_coordinates(37.7749, -122.4194)  # San Francisco

        # Distance to same location should be 0
        distance = clinic.calculate_distance_to(37.7749, -122.4194)
        assert distance == 0.0

        # Distance to Los Angeles (approximate)
        distance = clinic.calculate_distance_to(34.0522, -118.2437)
        assert distance is not None
        assert distance > 500  # Should be more than 500km

        # Test within radius
        assert clinic.is_within_radius(37.7749, -122.4194, 1.0) is True
        assert clinic.is_within_radius(34.0522, -118.2437, 100.0) is False

    def test_capacity_management(self):
        """Test capacity utilization functionality."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
            max_daily_appointments=100,
        )

        # Test capacity utilization
        utilization = clinic.get_capacity_utilization(50)
        assert utilization == 50.0

        utilization = clinic.get_capacity_utilization(100)
        assert utilization == 100.0

        utilization = clinic.get_capacity_utilization(120)
        assert utilization == 100.0  # Capped at 100%

        # Test at capacity
        assert clinic.is_at_capacity(50) is False
        assert clinic.is_at_capacity(100) is True
        assert clinic.is_at_capacity(120) is True

        # Test without max capacity set
        clinic.max_daily_appointments = None
        assert clinic.get_capacity_utilization(50) is None
        assert clinic.is_at_capacity(50) is False

    def test_display_methods(self):
        """Test display methods."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
            status=ClinicStatus.ACTIVE,
            type=ClinicType.EMERGENCY,
        )

        # Test status display
        assert clinic.get_status_display() == "Active"
        clinic.status = ClinicStatus.TEMPORARILY_CLOSED
        assert clinic.get_status_display() == "Temporarily Closed"

        # Test type display
        assert clinic.get_type_display() == "Emergency Clinic"
        clinic.type = ClinicType.GENERAL_PRACTICE
        assert clinic.get_type_display() == "General Practice"

    def test_repr(self):
        """Test string representation."""
        clinic = Clinic(
            name="Test Clinic",
            phone_number="555-123-4567",
            address_line1="123 Main Street",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )

        repr_str = repr(clinic)
        assert "Test Clinic" in repr_str
        assert "Anytown" in repr_str
        assert "active" in repr_str
