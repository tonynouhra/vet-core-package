"""
Tests for the User model.

This module contains unit tests for the User SQLAlchemy model,
testing model creation, relationships, and business logic.
"""

import pytest
import uuid
from datetime import datetime

from src.vet_core.models.user import User, UserRole, UserStatus


class TestUserModel:
    """Test cases for the User model."""
    
    def test_user_creation(self):
        """Test basic user creation with required fields."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.clerk_user_id == "clerk_123456"
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == UserRole.PET_OWNER  # Default role
        assert user.status == UserStatus.PENDING_VERIFICATION  # Default status
        assert user.email_notifications is True  # Default value
        assert user.sms_notifications is False  # Default value
        assert user.email_verified is False  # Default value
        assert user.phone_verified is False  # Default value
    
    def test_user_full_name_property(self):
        """Test the full_name property."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.full_name == "John Doe"
        
        # Test with empty last name
        user.last_name = ""
        assert user.full_name == "John"
        
        # Test with empty first name
        user.first_name = ""
        user.last_name = "Doe"
        assert user.full_name == "Doe"
    
    def test_user_display_name_property(self):
        """Test the display_name property."""
        user = User(
            clerk_user_id="clerk_123456",
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.display_name == "John Doe"
        
        # Test with empty names
        user.first_name = ""
        user.last_name = ""
        assert user.display_name == "john.doe"
    
    def test_user_is_active_property(self):
        """Test the is_active property."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status=UserStatus.ACTIVE
        )
        
        assert user.is_active is True
        
        # Test with inactive status
        user.status = UserStatus.INACTIVE
        assert user.is_active is False
        
        # Test with soft deleted user
        user.status = UserStatus.ACTIVE
        user.is_deleted = True
        assert user.is_active is False
    
    def test_user_is_verified_property(self):
        """Test the is_verified property."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.is_verified is False
        
        user.email_verified = True
        assert user.is_verified is True
    
    def test_user_has_complete_profile_property(self):
        """Test the has_complete_profile property."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        # Missing phone number
        assert user.has_complete_profile is False
        
        user.phone_number = "+1234567890"
        assert user.has_complete_profile is True
    
    def test_user_role_permissions(self):
        """Test role-based permission checking."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.VETERINARIAN,
            status=UserStatus.ACTIVE
        )
        
        # Veterinarian should have access to pet owner resources
        assert user.can_access_role(UserRole.PET_OWNER) is True
        assert user.can_access_role(UserRole.VET_TECH) is True
        assert user.can_access_role(UserRole.VETERINARIAN) is True
        
        # But not to admin resources
        assert user.can_access_role(UserRole.CLINIC_ADMIN) is False
        assert user.can_access_role(UserRole.PLATFORM_ADMIN) is False
        
        # Inactive user should not have access
        user.status = UserStatus.INACTIVE
        assert user.can_access_role(UserRole.PET_OWNER) is False
    
    def test_user_role_checking_methods(self):
        """Test role checking convenience methods."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        # Test pet owner
        user.role = UserRole.PET_OWNER
        assert user.is_pet_owner() is True
        assert user.is_veterinarian() is False
        assert user.is_staff() is False
        
        # Test veterinarian
        user.role = UserRole.VETERINARIAN
        assert user.is_pet_owner() is False
        assert user.is_veterinarian() is True
        assert user.is_staff() is True
        
        # Test vet tech
        user.role = UserRole.VET_TECH
        assert user.is_vet_tech() is True
        assert user.is_staff() is True
        
        # Test clinic admin
        user.role = UserRole.CLINIC_ADMIN
        assert user.is_clinic_admin() is True
        assert user.is_staff() is True
        
        # Test platform admin
        user.role = UserRole.PLATFORM_ADMIN
        assert user.is_platform_admin() is True
        assert user.is_staff() is True
    
    def test_user_preferences(self):
        """Test user preferences management."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        # Test getting preference with no preferences set
        assert user.get_preference("theme") is None
        assert user.get_preference("theme", "light") == "light"
        
        # Test setting preferences
        user.set_preference("theme", "dark")
        user.set_preference("language", "en")
        
        assert user.get_preference("theme") == "dark"
        assert user.get_preference("language") == "en"
        assert user.preferences == {"theme": "dark", "language": "en"}
    
    def test_user_profile_update(self):
        """Test profile update functionality."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        # Test valid profile update
        user.update_profile(
            first_name="Jane",
            phone_number="+1234567890",
            city="New York"
        )
        
        assert user.first_name == "Jane"
        assert user.phone_number == "+1234567890"
        assert user.city == "New York"
        
        # Test invalid field update
        with pytest.raises(ValueError, match="Invalid profile field"):
            user.update_profile(invalid_field="value")
    
    def test_user_status_methods(self):
        """Test user status management methods."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        # Test activation
        user.activate()
        assert user.status == UserStatus.ACTIVE
        
        # Test deactivation
        user.deactivate()
        assert user.status == UserStatus.INACTIVE
        
        # Test suspension
        user.suspend()
        assert user.status == UserStatus.SUSPENDED
    
    def test_user_verification_methods(self):
        """Test user verification methods."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status=UserStatus.PENDING_VERIFICATION
        )
        
        # Test email verification
        user.verify_email()
        assert user.email_verified is True
        assert user.status == UserStatus.ACTIVE  # Should activate pending user
        
        # Test phone verification
        user.verify_phone()
        assert user.phone_verified is True
    
    def test_user_repr(self):
        """Test string representation of User model."""
        user = User(
            clerk_user_id="clerk_123456",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.VETERINARIAN
        )
        
        # Note: id will be None until saved to database
        expected = f"<User(id={user.id}, email='test@example.com', role='veterinarian')>"
        assert repr(user) == expected


class TestUserEnums:
    """Test cases for User-related enums."""
    
    def test_user_role_enum_values(self):
        """Test UserRole enum values."""
        assert UserRole.PET_OWNER.value == "pet_owner"
        assert UserRole.VETERINARIAN.value == "veterinarian"
        assert UserRole.VET_TECH.value == "vet_tech"
        assert UserRole.CLINIC_ADMIN.value == "clinic_admin"
        assert UserRole.PLATFORM_ADMIN.value == "platform_admin"
    
    def test_user_status_enum_values(self):
        """Test UserStatus enum values."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING_VERIFICATION.value == "pending_verification"