"""
User model for the vet-core package.

This module contains the User SQLAlchemy model with authentication integration,
role-based access control, and user profile management.
"""

import enum
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class UserRole(enum.Enum):
    """Enumeration of user roles in the veterinary clinic platform."""
    
    PET_OWNER = "pet_owner"
    VETERINARIAN = "veterinarian"
    VET_TECH = "vet_tech"
    CLINIC_ADMIN = "clinic_admin"
    PLATFORM_ADMIN = "platform_admin"


class UserStatus(enum.Enum):
    """Enumeration of user account statuses."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(BaseModel):
    """
    User model with authentication integration and role-based access control.
    
    Supports multiple authentication providers (Clerk integration) and provides
    comprehensive user profile management with preferences storage.
    """
    
    __tablename__ = "users"
    
    def __init__(self, **kwargs):
        """Initialize User with default values."""
        # Set default values if not provided
        if 'role' not in kwargs:
            kwargs['role'] = UserRole.PET_OWNER
        if 'status' not in kwargs:
            kwargs['status'] = UserStatus.PENDING_VERIFICATION
        if 'email_notifications' not in kwargs:
            kwargs['email_notifications'] = True
        if 'sms_notifications' not in kwargs:
            kwargs['sms_notifications'] = False
        if 'email_verified' not in kwargs:
            kwargs['email_verified'] = False
        if 'phone_verified' not in kwargs:
            kwargs['phone_verified'] = False
        if 'country' not in kwargs:
            kwargs['country'] = "US"
            
        super().__init__(**kwargs)
    
    # Clerk integration fields
    clerk_user_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique identifier from Clerk authentication service"
    )
    
    # Basic user information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address"
    )
    
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's first name"
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's last name"
    )
    
    # Role-based access control
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.PET_OWNER,
        server_default=UserRole.PET_OWNER.value,
        index=True,
        comment="User's role in the platform"
    )
    
    # Account status
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION,
        server_default=UserStatus.PENDING_VERIFICATION.value,
        index=True,
        comment="Current status of the user account"
    )
    
    # Profile information
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="User's phone number"
    )
    
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to user's avatar image"
    )
    
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User's biography or description"
    )
    
    # Address information
    address_line1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary address line"
    )
    
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Secondary address line"
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City"
    )
    
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="State or province"
    )
    
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal or ZIP code"
    )
    
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="US",
        comment="Country code"
    )
    
    # User preferences and settings (JSONB for flexible storage)
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="User preferences and settings stored as JSON"
    )
    
    # Notification settings
    email_notifications: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether user wants to receive email notifications"
    )
    
    sms_notifications: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether user wants to receive SMS notifications"
    )
    
    # Account verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether user's email has been verified"
    )
    
    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether user's phone number has been verified"
    )
    
    # Terms and privacy
    terms_accepted_at: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Timestamp when user accepted terms of service"
    )
    
    privacy_accepted_at: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Timestamp when user accepted privacy policy"
    )
    
    # Database constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint('clerk_user_id', name='uq_users_clerk_user_id'),
        UniqueConstraint('email', name='uq_users_email'),
        
        # Composite indexes for efficient queries
        Index('idx_users_role_status', 'role', 'status'),
        Index('idx_users_email_status', 'email', 'status'),
        Index('idx_users_name_search', 'first_name', 'last_name'),
        Index('idx_users_location', 'city', 'state', 'country'),
        
        # Partial indexes for active users
        Index(
            'idx_users_active_email',
            'email',
            postgresql_where=(status == UserStatus.ACTIVE)
        ),
        Index(
            'idx_users_active_role',
            'role',
            postgresql_where=(status == UserStatus.ACTIVE)
        ),
        
        # GIN index for JSONB preferences
        Index('idx_users_preferences_gin', 'preferences', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        """String representation of the User model."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the user."""
        full_name = self.full_name
        return full_name if full_name else self.email.split('@')[0]
    
    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_deleted
    
    @property
    def is_verified(self) -> bool:
        """Check if the user has verified their email."""
        return self.email_verified
    
    @property
    def has_complete_profile(self) -> bool:
        """Check if the user has completed their profile."""
        required_fields = [
            self.first_name,
            self.last_name,
            self.email,
            self.phone_number
        ]
        return all(field for field in required_fields)
    
    def can_access_role(self, required_role: UserRole) -> bool:
        """
        Check if user has permission to access a role-protected resource.
        
        Args:
            required_role: The minimum role required for access
            
        Returns:
            True if user has sufficient permissions
        """
        if not self.is_active:
            return False
            
        # Define role hierarchy (higher values = more permissions)
        role_hierarchy = {
            UserRole.PET_OWNER: 1,
            UserRole.VET_TECH: 2,
            UserRole.VETERINARIAN: 3,
            UserRole.CLINIC_ADMIN: 4,
            UserRole.PLATFORM_ADMIN: 5,
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def is_pet_owner(self) -> bool:
        """Check if user is a pet owner."""
        return self.role == UserRole.PET_OWNER
    
    def is_veterinarian(self) -> bool:
        """Check if user is a veterinarian."""
        return self.role == UserRole.VETERINARIAN
    
    def is_vet_tech(self) -> bool:
        """Check if user is a veterinary technician."""
        return self.role == UserRole.VET_TECH
    
    def is_clinic_admin(self) -> bool:
        """Check if user is a clinic administrator."""
        return self.role == UserRole.CLINIC_ADMIN
    
    def is_platform_admin(self) -> bool:
        """Check if user is a platform administrator."""
        return self.role == UserRole.PLATFORM_ADMIN
    
    def is_staff(self) -> bool:
        """Check if user is staff (veterinarian, vet tech, or admin)."""
        staff_roles = {
            UserRole.VETERINARIAN,
            UserRole.VET_TECH,
            UserRole.CLINIC_ADMIN,
            UserRole.PLATFORM_ADMIN
        }
        return self.role in staff_roles
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference value.
        
        Args:
            key: The preference key
            default: Default value if key not found
            
        Returns:
            The preference value or default
        """
        if not self.preferences:
            return default
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference value.
        
        Args:
            key: The preference key
            value: The preference value
        """
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
    
    def update_profile(self, **kwargs) -> None:
        """
        Update user profile fields.
        
        Args:
            **kwargs: Profile fields to update
        """
        allowed_fields = {
            'first_name', 'last_name', 'phone_number', 'avatar_url', 'bio',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code',
            'country', 'email_notifications', 'sms_notifications'
        }
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
            else:
                raise ValueError(f"Invalid profile field: {field}")
    
    def activate(self) -> None:
        """Activate the user account."""
        self.status = UserStatus.ACTIVE
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.status = UserStatus.INACTIVE
    
    def suspend(self) -> None:
        """Suspend the user account."""
        self.status = UserStatus.SUSPENDED
    
    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        self.email_verified = True
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE
    
    def verify_phone(self) -> None:
        """Mark the user's phone number as verified."""
        self.phone_verified = True