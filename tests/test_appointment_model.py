"""
Tests for the Appointment model.

This module contains comprehensive tests for the Appointment SQLAlchemy model,
including validation, relationships, business logic, and scheduling capabilities.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.vet_core.models import (
    Appointment,
    AppointmentPriority,
    AppointmentStatus,
    Base,
    Pet,
    PetGender,
    PetSpecies,
    PetStatus,
    ServiceType,
    User,
    UserRole,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing relationships."""
    user = User(
        clerk_user_id="test_clerk_123",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        role=UserRole.PET_OWNER,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def sample_pet(session, sample_user):
    """Create a sample pet for testing appointments."""
    pet = Pet(
        owner_id=sample_user.id,
        name="Buddy",
        species=PetSpecies.DOG,
        breed="Golden Retriever",
        gender=PetGender.MALE,
        birth_date=date(2020, 5, 15),
    )
    session.add(pet)
    session.commit()
    return pet


@pytest.fixture
def sample_veterinarian_id():
    """Sample veterinarian ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_clinic_id():
    """Sample clinic ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_appointment_data(sample_pet, sample_veterinarian_id, sample_clinic_id):
    """Sample appointment data for testing."""
    scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)
    return {
        "pet_id": sample_pet.id,
        "veterinarian_id": sample_veterinarian_id,
        "clinic_id": sample_clinic_id,
        "scheduled_at": scheduled_time,
        "service_type": ServiceType.WELLNESS_EXAM,
        "reason": "Annual checkup",
        "duration_minutes": 45,
    }


class TestAppointmentModel:
    """Test cases for the Appointment model."""

    def test_appointment_creation_with_required_fields(
        self, session, sample_pet, sample_veterinarian_id, sample_clinic_id
    ):
        """Test creating an appointment with only required fields."""
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)

        appointment = Appointment(
            pet_id=sample_pet.id,
            veterinarian_id=sample_veterinarian_id,
            clinic_id=sample_clinic_id,
            scheduled_at=scheduled_time,
            service_type=ServiceType.WELLNESS_EXAM,
        )

        session.add(appointment)
        session.commit()

        assert appointment.id is not None
        assert appointment.pet_id == sample_pet.id
        assert appointment.veterinarian_id == sample_veterinarian_id
        assert appointment.clinic_id == sample_clinic_id
        # SQLite doesn't preserve timezone info, so compare timezone-naive datetimes
        assert appointment.scheduled_at.replace(tzinfo=None) == scheduled_time.replace(
            tzinfo=None
        )
        assert appointment.service_type == ServiceType.WELLNESS_EXAM
        assert appointment.status == AppointmentStatus.SCHEDULED  # Default value
        assert appointment.priority == AppointmentPriority.NORMAL  # Default value
        assert appointment.duration_minutes == 30  # Default value
        assert appointment.created_at is not None
        assert appointment.updated_at is not None

    def test_appointment_creation_with_all_fields(
        self, session, sample_appointment_data
    ):
        """Test creating an appointment with all fields populated."""
        appointment_data = sample_appointment_data.copy()
        appointment_data.update(
            {
                "status": AppointmentStatus.CONFIRMED,
                "priority": AppointmentPriority.HIGH,
                "notes": "Pet seems anxious during visits",
                "internal_notes": "Check vaccination records",
                "estimated_cost": Decimal("150.00"),
                "follow_up_needed": True,
                "follow_up_instructions": "Schedule dental cleaning in 6 months",
            }
        )

        appointment = Appointment(**appointment_data)
        session.add(appointment)
        session.commit()

        assert appointment.status == AppointmentStatus.CONFIRMED
        assert appointment.priority == AppointmentPriority.HIGH
        assert appointment.notes == "Pet seems anxious during visits"
        assert appointment.internal_notes == "Check vaccination records"
        assert appointment.estimated_cost == Decimal("150.00")
        assert appointment.follow_up_needed is True
        assert (
            appointment.follow_up_instructions == "Schedule dental cleaning in 6 months"
        )

    def test_appointment_default_values(self, session, sample_appointment_data):
        """Test that default values are set correctly."""
        # Remove duration_minutes from fixture data to test the default value
        appointment_data = sample_appointment_data.copy()
        appointment_data.pop("duration_minutes", None)
        appointment = Appointment(**appointment_data)

        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.priority == AppointmentPriority.NORMAL
        assert appointment.duration_minutes == 30

    def test_appointment_status_transitions(self, session, sample_appointment_data):
        """Test appointment status transitions and business logic."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Test confirm
        assert appointment.status == AppointmentStatus.SCHEDULED
        appointment.confirm()
        assert appointment.status == AppointmentStatus.CONFIRMED

        # Test check-in
        assert appointment.can_check_in()
        appointment.check_in()
        assert appointment.status == AppointmentStatus.CHECKED_IN
        assert appointment.checked_in_at is not None

        # Test start
        assert appointment.can_start()
        appointment.start()
        assert appointment.status == AppointmentStatus.IN_PROGRESS
        assert appointment.started_at is not None

        # Test complete
        assert appointment.can_complete()
        appointment.complete(
            actual_cost=Decimal("175.50"),
            follow_up_needed=True,
            follow_up_instructions="Return in 2 weeks",
            next_appointment_days=14,
        )
        assert appointment.status == AppointmentStatus.COMPLETED
        assert appointment.completed_at is not None
        assert appointment.actual_cost == Decimal("175.50")
        assert appointment.follow_up_needed is True
        assert appointment.follow_up_instructions == "Return in 2 weeks"
        assert appointment.next_appointment_recommended_days == 14

    def test_appointment_cancellation(self, session, sample_appointment_data):
        """Test appointment cancellation."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Test cancellation from scheduled status
        assert appointment.can_be_cancelled()
        appointment.cancel("Pet owner requested cancellation")
        assert appointment.status == AppointmentStatus.CANCELLED
        assert appointment.cancelled_at is not None
        assert appointment.cancellation_reason == "Pet owner requested cancellation"

        # Test that cancelled appointment cannot be cancelled again
        assert not appointment.can_be_cancelled()

    def test_appointment_rescheduling(self, session, sample_appointment_data):
        """Test appointment rescheduling."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        original_time = appointment.scheduled_at
        new_time = original_time + timedelta(days=2)

        # Test rescheduling
        assert appointment.can_be_rescheduled()
        appointment.reschedule(new_time)
        assert appointment.scheduled_at == new_time
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert original_time.isoformat() in appointment.internal_notes

    def test_appointment_no_show(self, session, sample_appointment_data):
        """Test marking appointment as no-show."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        appointment.mark_no_show()
        assert appointment.status == AppointmentStatus.NO_SHOW

    def test_appointment_properties(self, session, sample_appointment_data):
        """Test appointment computed properties."""
        appointment = Appointment(**sample_appointment_data)
        appointment.priority = AppointmentPriority.EMERGENCY
        appointment.service_type = ServiceType.EMERGENCY

        # Test boolean properties
        assert appointment.is_active
        assert not appointment.is_completed
        assert not appointment.is_cancelled
        assert appointment.is_emergency
        assert appointment.is_urgent

        # Test estimated end time
        expected_end = appointment.scheduled_at + timedelta(
            minutes=appointment.duration_minutes
        )
        assert appointment.estimated_end_time == expected_end

        # Complete the appointment to test duration calculation
        appointment.status = AppointmentStatus.IN_PROGRESS
        appointment.started_at = datetime.now(timezone.utc)
        appointment.completed_at = appointment.started_at + timedelta(minutes=35)

        assert appointment.actual_duration_minutes == 35

    def test_appointment_cost_calculations(self, session, sample_appointment_data):
        """Test cost-related calculations."""
        appointment = Appointment(**sample_appointment_data)
        appointment.estimated_cost = Decimal("100.00")
        appointment.actual_cost = Decimal("125.50")

        assert appointment.cost_variance == Decimal("25.50")

    def test_appointment_wait_time_calculation(self, session, sample_appointment_data):
        """Test wait time calculation."""
        appointment = Appointment(**sample_appointment_data)

        check_in_time = datetime.now(timezone.utc)
        start_time = check_in_time + timedelta(minutes=15)

        appointment.checked_in_at = check_in_time
        appointment.started_at = start_time

        assert appointment.wait_time_minutes == 15

    def test_appointment_overdue_check(self, session, sample_appointment_data):
        """Test overdue appointment detection."""
        # Create appointment in the past
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        appointment_data = sample_appointment_data.copy()
        appointment_data["scheduled_at"] = past_time

        appointment = Appointment(**appointment_data)

        # Should be overdue if not started
        assert appointment.is_overdue

        # Should not be overdue if started
        appointment.started_at = datetime.now(timezone.utc)
        assert not appointment.is_overdue

        # Should not be overdue if not active
        appointment.status = AppointmentStatus.CANCELLED
        assert not appointment.is_overdue

    def test_appointment_notes_management(self, session, sample_appointment_data):
        """Test adding notes to appointments."""
        appointment = Appointment(**sample_appointment_data)

        # Test adding regular note
        appointment.add_note("Pet arrived early")
        assert "Pet arrived early" in appointment.notes

        # Test adding internal note
        appointment.add_note("Needs blood work", internal=True)
        assert "Needs blood work" in appointment.internal_notes

        # Test adding multiple notes
        appointment.add_note("Owner has questions about diet")
        assert "Pet arrived early" in appointment.notes
        assert "Owner has questions about diet" in appointment.notes

    def test_appointment_cost_update(self, session, sample_appointment_data):
        """Test updating appointment cost estimate."""
        appointment = Appointment(**sample_appointment_data)

        appointment.update_cost_estimate(Decimal("200.00"))
        assert appointment.estimated_cost == Decimal("200.00")

        # Test negative cost validation
        with pytest.raises(ValueError, match="Estimated cost cannot be negative"):
            appointment.update_cost_estimate(Decimal("-50.00"))

    def test_appointment_display_methods(self, session, sample_appointment_data):
        """Test display methods for human-readable output."""
        appointment = Appointment(**sample_appointment_data)
        appointment.duration_minutes = 90
        appointment.status = AppointmentStatus.IN_PROGRESS
        appointment.service_type = ServiceType.DENTAL_CLEANING
        appointment.priority = AppointmentPriority.HIGH

        # Test duration display
        assert appointment.get_duration_display() == "1h 30m"

        appointment.duration_minutes = 60
        assert appointment.get_duration_display() == "1 hour"

        appointment.duration_minutes = 30
        assert appointment.get_duration_display() == "30 minutes"

        # Test status display
        assert appointment.get_status_display() == "In Progress"

        # Test service display
        assert appointment.get_service_display() == "Dental Cleaning"

        # Test priority display
        assert appointment.get_priority_display() == "High"

    def test_appointment_validation_constraints(self, session, sample_appointment_data):
        """Test database constraints and validation."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Test that we can retrieve the appointment
        retrieved = session.query(Appointment).filter_by(id=appointment.id).first()
        assert retrieved is not None
        assert retrieved.pet_id == appointment.pet_id
        assert retrieved.veterinarian_id == appointment.veterinarian_id
        assert retrieved.clinic_id == appointment.clinic_id

    def test_appointment_invalid_status_transitions(
        self, session, sample_appointment_data
    ):
        """Test invalid status transitions raise appropriate errors."""
        appointment = Appointment(**sample_appointment_data)
        appointment.status = AppointmentStatus.COMPLETED
        session.add(appointment)
        session.commit()

        # Cannot confirm completed appointment
        with pytest.raises(ValueError, match="Cannot confirm appointment"):
            appointment.confirm()

        # Cannot check in completed appointment
        with pytest.raises(ValueError, match="Cannot check in appointment"):
            appointment.check_in()

        # Cannot start completed appointment
        with pytest.raises(ValueError, match="Cannot start appointment"):
            appointment.start()

        # Cannot complete already completed appointment
        with pytest.raises(ValueError, match="Cannot complete appointment"):
            appointment.complete()

    def test_appointment_emergency_priority_detection(
        self, session, sample_appointment_data
    ):
        """Test emergency appointment detection."""
        appointment = Appointment(**sample_appointment_data)

        # Test emergency service type
        appointment.service_type = ServiceType.EMERGENCY
        appointment.priority = AppointmentPriority.NORMAL
        assert appointment.is_emergency

        # Test emergency priority
        appointment.service_type = ServiceType.WELLNESS_EXAM
        appointment.priority = AppointmentPriority.EMERGENCY
        assert appointment.is_emergency

        # Test urgent priority
        appointment.priority = AppointmentPriority.URGENT
        assert appointment.is_urgent
        assert not appointment.is_emergency  # Urgent but not emergency

    def test_appointment_string_representation(self, session, sample_appointment_data):
        """Test string representation of appointment."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        repr_str = repr(appointment)
        assert "Appointment" in repr_str
        assert str(appointment.id) in repr_str
        assert str(appointment.pet_id) in repr_str
        assert appointment.status.value in repr_str

    def test_appointment_soft_delete_inheritance(
        self, session, sample_appointment_data
    ):
        """Test that appointment inherits soft delete functionality from BaseModel."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Test soft delete
        appointment.soft_delete()
        assert appointment.is_deleted
        assert appointment.deleted_at is not None

        # Test restore
        appointment.restore()
        assert not appointment.is_deleted
        assert appointment.deleted_at is None


class TestAppointmentEnums:
    """Test cases for appointment-related enums."""

    def test_appointment_status_enum(self):
        """Test AppointmentStatus enum values."""
        assert AppointmentStatus.SCHEDULED.value == "scheduled"
        assert AppointmentStatus.CONFIRMED.value == "confirmed"
        assert AppointmentStatus.CHECKED_IN.value == "checked_in"
        assert AppointmentStatus.IN_PROGRESS.value == "in_progress"
        assert AppointmentStatus.COMPLETED.value == "completed"
        assert AppointmentStatus.CANCELLED.value == "cancelled"
        assert AppointmentStatus.NO_SHOW.value == "no_show"
        assert AppointmentStatus.RESCHEDULED.value == "rescheduled"

    def test_service_type_enum(self):
        """Test ServiceType enum values."""
        assert ServiceType.WELLNESS_EXAM.value == "wellness_exam"
        assert ServiceType.VACCINATION.value == "vaccination"
        assert ServiceType.DENTAL_CLEANING.value == "dental_cleaning"
        assert ServiceType.SURGERY.value == "surgery"
        assert ServiceType.EMERGENCY.value == "emergency"
        assert ServiceType.GROOMING.value == "grooming"
        assert ServiceType.BOARDING.value == "boarding"
        assert ServiceType.CONSULTATION.value == "consultation"
        assert ServiceType.FOLLOW_UP.value == "follow_up"
        assert ServiceType.DIAGNOSTIC.value == "diagnostic"
        assert ServiceType.TREATMENT.value == "treatment"
        assert ServiceType.OTHER.value == "other"

    def test_appointment_priority_enum(self):
        """Test AppointmentPriority enum values."""
        assert AppointmentPriority.LOW.value == "low"
        assert AppointmentPriority.NORMAL.value == "normal"
        assert AppointmentPriority.HIGH.value == "high"
        assert AppointmentPriority.URGENT.value == "urgent"
        assert AppointmentPriority.EMERGENCY.value == "emergency"


class TestAppointmentBusinessLogic:
    """Test cases for appointment business logic and edge cases."""

    def test_appointment_workflow_complete_cycle(
        self, session, sample_appointment_data
    ):
        """Test complete appointment workflow from creation to completion."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Initial state
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.is_active

        # Confirm appointment
        appointment.confirm()
        assert appointment.status == AppointmentStatus.CONFIRMED

        # Check in
        appointment.check_in()
        assert appointment.status == AppointmentStatus.CHECKED_IN
        assert appointment.checked_in_at is not None

        # Start appointment
        appointment.start()
        assert appointment.status == AppointmentStatus.IN_PROGRESS
        assert appointment.started_at is not None

        # Complete appointment
        appointment.complete(actual_cost=Decimal("150.00"), follow_up_needed=False)
        assert appointment.status == AppointmentStatus.COMPLETED
        assert appointment.completed_at is not None
        assert appointment.actual_cost == Decimal("150.00")
        assert appointment.follow_up_needed is False

        # Verify final state
        assert not appointment.is_active
        assert appointment.is_completed

    def test_appointment_cancellation_workflow(self, session, sample_appointment_data):
        """Test appointment cancellation workflow."""
        appointment = Appointment(**sample_appointment_data)
        session.add(appointment)
        session.commit()

        # Can cancel from scheduled
        assert appointment.can_be_cancelled()
        appointment.cancel("Owner requested cancellation")
        assert appointment.status == AppointmentStatus.CANCELLED
        assert appointment.is_cancelled
        assert not appointment.is_active

        # Cannot perform other actions after cancellation
        assert not appointment.can_check_in()
        assert not appointment.can_start()
        assert not appointment.can_complete()
        assert not appointment.can_be_rescheduled()

    def test_appointment_time_calculations_edge_cases(
        self, session, sample_appointment_data
    ):
        """Test edge cases in time calculations."""
        appointment = Appointment(**sample_appointment_data)

        # Test with no times set
        assert appointment.actual_duration_minutes is None
        assert appointment.wait_time_minutes is None

        # Test with only start time
        appointment.started_at = datetime.now(timezone.utc)
        assert appointment.actual_duration_minutes is None

        # Test with only check-in time
        appointment.started_at = None
        appointment.checked_in_at = datetime.now(timezone.utc)
        assert appointment.wait_time_minutes is None
