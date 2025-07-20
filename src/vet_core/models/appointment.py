"""
Appointment model for the vet-core package.

This module contains the Appointment SQLAlchemy model with scheduling capabilities,
service type categorization, and relationships to Pet, Veterinarian, and Clinic models.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class AppointmentStatus(enum.Enum):
    """Enumeration of appointment statuses."""
    
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class ServiceType(enum.Enum):
    """
    Enumeration of veterinary service types.
    
    When using OTHER, provide a description in service_type_other_description field
    (e.g., 'acupuncture', 'behavioral training', 'nail trimming', 'microchipping').
    """
    
    WELLNESS_EXAM = "wellness_exam"
    VACCINATION = "vaccination"
    DENTAL_CLEANING = "dental_cleaning"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    GROOMING = "grooming"
    BOARDING = "boarding"
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    DIAGNOSTIC = "diagnostic"
    TREATMENT = "treatment"
    OTHER = "other"


class AppointmentPriority(enum.Enum):
    """Enumeration of appointment priority levels."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class Appointment(BaseModel):
    """
    Appointment model with comprehensive scheduling capabilities.
    
    Supports flexible scheduling system with datetime handling, service type
    categorization, status tracking, and relationships to pet, veterinarian, and clinic.
    """
    
    __tablename__ = "appointments"
    
    def __init__(self, **kwargs):
        """Initialize Appointment with default values."""
        # Set default values if not provided
        if 'status' not in kwargs:
            kwargs['status'] = AppointmentStatus.SCHEDULED
        if 'priority' not in kwargs:
            kwargs['priority'] = AppointmentPriority.NORMAL
        if 'duration_minutes' not in kwargs:
            kwargs['duration_minutes'] = 30
            
        super().__init__(**kwargs)
    
    # Relationship foreign keys
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the pet for this appointment"
    )
    
    veterinarian_id: Mapped[uuid.UUID] = mapped_column(
        # Will reference veterinarians.id when that model is created
        nullable=False,
        index=True,
        comment="UUID of the assigned veterinarian"
    )
    
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        # Will reference clinics.id when that model is created
        nullable=False,
        index=True,
        comment="UUID of the clinic where appointment takes place"
    )
    
    # Scheduling information
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Scheduled date and time for the appointment"
    )
    
    duration_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
        comment="Expected duration of the appointment in minutes"
    )
    
    # Appointment details
    service_type: Mapped[ServiceType] = mapped_column(
        Enum(ServiceType),
        nullable=False,
        index=True,
        comment="Type of veterinary service"
    )
    
    service_type_other_description: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Description when service_type is 'other' (e.g., 'acupuncture', 'behavioral training', 'nail trimming')"
    )
    
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        index=True,
        comment="Current status of the appointment"
    )
    
    priority: Mapped[AppointmentPriority] = mapped_column(
        Enum(AppointmentPriority),
        nullable=False,
        default=AppointmentPriority.NORMAL,
        index=True,
        comment="Priority level of the appointment"
    )
    
    # Appointment notes and details
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for the appointment or chief complaint"
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about the appointment"
    )
    
    internal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal staff notes not visible to pet owner"
    )
    
    # Financial information
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),  # Up to 99,999,999.99
        nullable=True,
        comment="Estimated cost of the appointment"
    )
    
    actual_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),  # Up to 99,999,999.99
        nullable=True,
        comment="Actual cost of the appointment"
    )
    
    # Timing information
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the pet was checked in for the appointment"
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the appointment actually started"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the appointment was completed"
    )
    
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the appointment was cancelled"
    )
    
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for appointment cancellation"
    )
    
    # Follow-up information
    follow_up_needed: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether a follow-up appointment is needed"
    )
    
    follow_up_instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Instructions for follow-up care"
    )
    
    next_appointment_recommended_days: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Recommended days until next appointment"
    )
    
    # Database constraints and indexes
    __table_args__ = (
        # Check constraints for data integrity
        CheckConstraint(
            'duration_minutes > 0',
            name='ck_appointments_duration_positive'
        ),
        CheckConstraint(
            "service_type != 'other' OR service_type_other_description IS NOT NULL",
            name='ck_appointments_service_other_description_required'
        ),
        CheckConstraint(
            'estimated_cost IS NULL OR estimated_cost >= 0',
            name='ck_appointments_estimated_cost_non_negative'
        ),
        CheckConstraint(
            'actual_cost IS NULL OR actual_cost >= 0',
            name='ck_appointments_actual_cost_non_negative'
        ),
        CheckConstraint(
            'scheduled_at > created_at',
            name='ck_appointments_scheduled_after_created'
        ),
        CheckConstraint(
            'checked_in_at IS NULL OR checked_in_at >= created_at',
            name='ck_appointments_checked_in_after_created'
        ),
        CheckConstraint(
            'started_at IS NULL OR started_at >= created_at',
            name='ck_appointments_started_after_created'
        ),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= created_at',
            name='ck_appointments_completed_after_created'
        ),
        CheckConstraint(
            'cancelled_at IS NULL OR cancelled_at >= created_at',
            name='ck_appointments_cancelled_after_created'
        ),
        CheckConstraint(
            'next_appointment_recommended_days IS NULL OR next_appointment_recommended_days > 0',
            name='ck_appointments_next_appointment_days_positive'
        ),
        
        # Composite indexes for efficient appointment queries
        Index('idx_appointments_pet_scheduled', 'pet_id', 'scheduled_at'),
        Index('idx_appointments_vet_scheduled', 'veterinarian_id', 'scheduled_at'),
        Index('idx_appointments_clinic_scheduled', 'clinic_id', 'scheduled_at'),
        Index('idx_appointments_status_scheduled', 'status', 'scheduled_at'),
        Index('idx_appointments_service_scheduled', 'service_type', 'scheduled_at'),
        Index('idx_appointments_priority_scheduled', 'priority', 'scheduled_at'),
        
        # Indexes for date-based queries
        Index('idx_appointments_scheduled_date', 'scheduled_at'),
        Index('idx_appointments_created_date', 'created_at'),
        
        # Composite indexes for common query patterns
        Index('idx_appointments_pet_status', 'pet_id', 'status'),
        Index('idx_appointments_vet_status', 'veterinarian_id', 'status'),
        Index('idx_appointments_clinic_status', 'clinic_id', 'status'),
        Index('idx_appointments_status_service', 'status', 'service_type'),
        
        # Partial indexes for active appointments
        Index(
            'idx_appointments_active_scheduled',
            'scheduled_at',
            postgresql_where=(status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]))
        ),
        Index(
            'idx_appointments_active_pet',
            'pet_id',
            postgresql_where=(status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]))
        ),
        Index(
            'idx_appointments_active_vet',
            'veterinarian_id',
            postgresql_where=(status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]))
        ),
        
        # Indexes for emergency and urgent appointments
        Index(
            'idx_appointments_urgent',
            'scheduled_at',
            postgresql_where=(priority.in_([
                AppointmentPriority.URGENT,
                AppointmentPriority.EMERGENCY
            ]))
        ),
        
        # Index for follow-up appointments
        Index(
            'idx_appointments_follow_up_needed',
            'completed_at',
            postgresql_where=(follow_up_needed == True)
        ),
        
        # Index for service type other description
        Index('idx_appointments_service_other_description', 'service_type_other_description'),
    )
    
    # Relationships will be defined when other models are available
    # pet = relationship("Pet", back_populates="appointments")
    # veterinarian = relationship("Veterinarian", back_populates="appointments")
    # clinic = relationship("Clinic", back_populates="appointments")
    
    def __repr__(self) -> str:
        """String representation of the Appointment model."""
        return (
            f"<Appointment(id={self.id}, pet_id={self.pet_id}, "
            f"scheduled_at='{self.scheduled_at}', status='{self.status.value}')>"
        )
    
    @property
    def is_active(self) -> bool:
        """Check if the appointment is active (not cancelled, completed, or no-show)."""
        active_statuses = {
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_PROGRESS
        }
        return self.status in active_statuses and not self.is_deleted
    
    @property
    def is_completed(self) -> bool:
        """Check if the appointment is completed."""
        return self.status == AppointmentStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """Check if the appointment is cancelled."""
        return self.status == AppointmentStatus.CANCELLED
    
    @property
    def is_emergency(self) -> bool:
        """Check if the appointment is an emergency."""
        return (
            self.priority == AppointmentPriority.EMERGENCY or
            self.service_type == ServiceType.EMERGENCY
        )
    
    @property
    def is_urgent(self) -> bool:
        """Check if the appointment is urgent or emergency."""
        return self.priority in {AppointmentPriority.URGENT, AppointmentPriority.EMERGENCY}
    
    @property
    def estimated_end_time(self) -> datetime:
        """Calculate the estimated end time of the appointment."""
        from datetime import timedelta
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)
    
    @property
    def actual_duration_minutes(self) -> Optional[int]:
        """Calculate the actual duration of the appointment if completed."""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return int(duration.total_seconds() / 60)
        return None
    
    @property
    def wait_time_minutes(self) -> Optional[int]:
        """Calculate the wait time between check-in and start."""
        if self.checked_in_at and self.started_at:
            wait_time = self.started_at - self.checked_in_at
            return int(wait_time.total_seconds() / 60)
        return None
    
    @property
    def is_overdue(self) -> bool:
        """Check if the appointment is overdue (past scheduled time and not started)."""
        if not self.is_active:
            return False
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return now > self.scheduled_at and self.started_at is None
    
    @property
    def cost_variance(self) -> Optional[Decimal]:
        """Calculate the variance between estimated and actual cost."""
        if self.estimated_cost is not None and self.actual_cost is not None:
            return self.actual_cost - self.estimated_cost
        return None
    
    def can_be_cancelled(self) -> bool:
        """Check if the appointment can be cancelled."""
        cancellable_statuses = {
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        }
        return self.status in cancellable_statuses and not self.is_deleted
    
    def can_be_rescheduled(self) -> bool:
        """Check if the appointment can be rescheduled."""
        reschedulable_statuses = {
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        }
        return self.status in reschedulable_statuses and not self.is_deleted
    
    def can_check_in(self) -> bool:
        """Check if the pet can be checked in for the appointment."""
        return (
            self.status == AppointmentStatus.CONFIRMED and
            not self.is_deleted and
            self.checked_in_at is None
        )
    
    def can_start(self) -> bool:
        """Check if the appointment can be started."""
        return (
            self.status == AppointmentStatus.CHECKED_IN and
            not self.is_deleted and
            self.started_at is None
        )
    
    def can_complete(self) -> bool:
        """Check if the appointment can be completed."""
        return (
            self.status == AppointmentStatus.IN_PROGRESS and
            not self.is_deleted and
            self.completed_at is None
        )
    
    def confirm(self) -> None:
        """Confirm the appointment."""
        if self.status == AppointmentStatus.SCHEDULED:
            self.status = AppointmentStatus.CONFIRMED
        else:
            raise ValueError(f"Cannot confirm appointment with status {self.status.value}")
    
    def check_in(self) -> None:
        """Check in the pet for the appointment."""
        if not self.can_check_in():
            raise ValueError(f"Cannot check in appointment with status {self.status.value}")
        
        from datetime import datetime, timezone
        self.status = AppointmentStatus.CHECKED_IN
        self.checked_in_at = datetime.now(timezone.utc)
    
    def start(self) -> None:
        """Start the appointment."""
        if not self.can_start():
            raise ValueError(f"Cannot start appointment with status {self.status.value}")
        
        from datetime import datetime, timezone
        self.status = AppointmentStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self, actual_cost: Optional[Decimal] = None,
                follow_up_needed: Optional[bool] = None,
                follow_up_instructions: Optional[str] = None,
                next_appointment_days: Optional[int] = None) -> None:
        """
        Complete the appointment.
        
        Args:
            actual_cost: The actual cost of the appointment
            follow_up_needed: Whether a follow-up is needed
            follow_up_instructions: Instructions for follow-up care
            next_appointment_days: Recommended days until next appointment
        """
        if not self.can_complete():
            raise ValueError(f"Cannot complete appointment with status {self.status.value}")
        
        from datetime import datetime, timezone
        self.status = AppointmentStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        
        if actual_cost is not None:
            self.actual_cost = actual_cost
        if follow_up_needed is not None:
            self.follow_up_needed = follow_up_needed
        if follow_up_instructions is not None:
            self.follow_up_instructions = follow_up_instructions
        if next_appointment_days is not None:
            self.next_appointment_recommended_days = next_appointment_days
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel the appointment.
        
        Args:
            reason: Reason for cancellation
        """
        if not self.can_be_cancelled():
            raise ValueError(f"Cannot cancel appointment with status {self.status.value}")
        
        from datetime import datetime, timezone
        self.status = AppointmentStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        if reason:
            self.cancellation_reason = reason
    
    def reschedule(self, new_scheduled_at: datetime) -> None:
        """
        Reschedule the appointment to a new time.
        
        Args:
            new_scheduled_at: New scheduled date and time
        """
        if not self.can_be_rescheduled():
            raise ValueError(f"Cannot reschedule appointment with status {self.status.value}")
        
        # Store old scheduled time in notes for audit trail
        old_time = self.scheduled_at.isoformat()
        audit_note = f"Rescheduled from {old_time}"
        
        if self.internal_notes:
            self.internal_notes += f"\n{audit_note}"
        else:
            self.internal_notes = audit_note
        
        self.scheduled_at = new_scheduled_at
        self.status = AppointmentStatus.SCHEDULED  # Reset to scheduled
    
    def mark_no_show(self) -> None:
        """Mark the appointment as a no-show."""
        if self.status not in {AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED}:
            raise ValueError(f"Cannot mark no-show for appointment with status {self.status.value}")
        
        self.status = AppointmentStatus.NO_SHOW
    
    def update_cost_estimate(self, estimated_cost: Decimal) -> None:
        """
        Update the estimated cost of the appointment.
        
        Args:
            estimated_cost: New estimated cost
        """
        if estimated_cost < 0:
            raise ValueError("Estimated cost cannot be negative")
        self.estimated_cost = estimated_cost
    
    def add_note(self, note: str, internal: bool = False) -> None:
        """
        Add a note to the appointment.
        
        Args:
            note: The note to add
            internal: Whether this is an internal note (not visible to pet owner)
        """
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        formatted_note = f"[{timestamp}] {note}"
        
        if internal:
            if self.internal_notes:
                self.internal_notes += f"\n{formatted_note}"
            else:
                self.internal_notes = formatted_note
        else:
            if self.notes:
                self.notes += f"\n{formatted_note}"
            else:
                self.notes = formatted_note
    
    def get_duration_display(self) -> str:
        """Get a human-readable duration display."""
        if self.duration_minutes < 60:
            return f"{self.duration_minutes} minutes"
        else:
            hours = self.duration_minutes // 60
            minutes = self.duration_minutes % 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours}h {minutes}m"
    
    def get_status_display(self) -> str:
        """Get a human-readable status display."""
        status_display = {
            AppointmentStatus.SCHEDULED: "Scheduled",
            AppointmentStatus.CONFIRMED: "Confirmed",
            AppointmentStatus.CHECKED_IN: "Checked In",
            AppointmentStatus.IN_PROGRESS: "In Progress",
            AppointmentStatus.COMPLETED: "Completed",
            AppointmentStatus.CANCELLED: "Cancelled",
            AppointmentStatus.NO_SHOW: "No Show",
            AppointmentStatus.RESCHEDULED: "Rescheduled"
        }
        return status_display.get(self.status, self.status.value.title())
    
    def get_service_display(self) -> str:
        """Get a human-readable service type display."""
        if self.service_type == ServiceType.OTHER and self.service_type_other_description:
            return self.service_type_other_description.title()
        
        service_display = {
            ServiceType.WELLNESS_EXAM: "Wellness Exam",
            ServiceType.VACCINATION: "Vaccination",
            ServiceType.DENTAL_CLEANING: "Dental Cleaning",
            ServiceType.SURGERY: "Surgery",
            ServiceType.EMERGENCY: "Emergency",
            ServiceType.GROOMING: "Grooming",
            ServiceType.BOARDING: "Boarding",
            ServiceType.CONSULTATION: "Consultation",
            ServiceType.FOLLOW_UP: "Follow-up",
            ServiceType.DIAGNOSTIC: "Diagnostic",
            ServiceType.TREATMENT: "Treatment",
            ServiceType.OTHER: "Other"
        }
        return service_display.get(self.service_type, self.service_type.value.title())
    
    def set_other_service_type(self, description: str) -> None:
        """
        Set the service type to 'other' with a custom description.
        
        Args:
            description: Description of the service (e.g., 'acupuncture', 'behavioral training')
        """
        if not description or not description.strip():
            raise ValueError("Description is required when setting service type to 'other'")
        self.service_type = ServiceType.OTHER
        self.service_type_other_description = description.strip().lower()
    
    def validate_service_type_description(self) -> bool:
        """
        Validate that if service_type is 'other', a description is provided.
        
        Returns:
            True if valid, False otherwise
        """
        if self.service_type == ServiceType.OTHER:
            return bool(self.service_type_other_description and self.service_type_other_description.strip())
        return True
    
    def get_priority_display(self) -> str:
        """Get a human-readable priority display."""
        priority_display = {
            AppointmentPriority.LOW: "Low",
            AppointmentPriority.NORMAL: "Normal",
            AppointmentPriority.HIGH: "High",
            AppointmentPriority.URGENT: "Urgent",
            AppointmentPriority.EMERGENCY: "Emergency"
        }
        return priority_display.get(self.priority, self.priority.value.title())