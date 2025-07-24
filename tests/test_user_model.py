"""
Tests for the User model.

This module contains comprehensive unit tests for the User SQLAlchemy model,
testing model creation, relationships, validation, and business logic.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from vet_core.models.user import User, UserRole, UserStatus
from vet_core.models.pet import Pet, PetSpecies
from vet_core.models.veterinarian import Veterinarian


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
        assert user.country == "US"  # Default value
    
    @pytest_asyncio.fixture
    async def test_user_database_creation(self, async_session, user_factory):
        """Test user creation and persistence in database."""
        user_data = {
            "clerk_user_id": "clerk_db_test",
            "email": "dbtest@example.com",
            "first_name": "Database",
            "last_name": "Test",
            "phone_number": "+1234567890",
            "role": UserRole.VETERINARIAN
        }
        
        user = await user_factory.create(async_session, **user_data)
        
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.clerk_user_id == "clerk_db_test"
        assert user.email == "dbtest@example.com"
        assert user.role == UserRole.VETERINARIAN
        assert user.is_active  # Should be active by default
        
        return user
    
    def test_user_creation_with_all_fields(self):
        """Test user creation with all optional fields."""
        user = User(
            clerk_user_id="clerk_full_test",
            email="fulltest@example.com",
            first_name="Full",
            last_name="Test",
            role=UserRole.CLINIC_ADMIN,
            status=UserStatus.ACTIVE,
            phone_number="+1987654321",
            avatar_url="https://example.com/avatar.jpg",
            bio="Test user biography",
            address_line1="123 Test Street",
            address_line2="Apt 4B",
            city="Test City",
            state="CA",
            postal_code="12345",
            country="US",
            preferences={"theme": "dark", "language": "en"},
            email_notifications=False,
            sms_notifications=True,
            email_verified=True,
            phone_verified=True,
            terms_accepted_at="2023-01-01T00:00:00Z",
            privacy_accepted_at="2023-01-01T00:00:00Z"
        )
        
        assert user.role == UserRole.CLINIC_ADMIN
        assert user.status == UserStatus.ACTIVE
        assert user.phone_number == "+1987654321"
        assert user.avatar_url == "https://example.com/avatar.jpg"
        assert user.bio == "Test user biography"
        assert user.address_line1 == "123 Test Street"
        assert user.address_line2 == "Apt 4B"
        assert user.city == "Test City"
        assert user.state == "CA"
        assert user.postal_code == "12345"
        assert user.country == "US"
        assert user.preferences == {"theme": "dark", "language": "en"}
        assert user.email_notifications is False
        assert user.sms_notifications is True
        assert user.email_verified is True
        assert user.phone_verified is True
        assert user.terms_accepted_at == "2023-01-01T00:00:00Z"
        assert user.privacy_accepted_at == "2023-01-01T00:00:00Z"
    
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
    
    @pytest_asyncio.fixture
    async def test_user_pet_relationship(self, async_session, user_factory, pet_factory):
        """Test user-pet relationship functionality."""
        # Create user
        user = await user_factory.create(async_session)
        
        # Create pets for the user
        pet1 = await pet_factory.create(async_session, owner=user, name="Buddy")
        pet2 = await pet_factory.create(async_session, owner=user, name="Max")
        
        # Test relationship access
        await async_session.refresh(user, ["pets"])
        assert len(user.pets) == 2
        pet_names = {pet.name for pet in user.pets}
        assert pet_names == {"Buddy", "Max"}
        
        # Test reverse relationship
        assert pet1.owner == user
        assert pet2.owner == user
    
    @pytest_asyncio.fixture
    async def test_user_veterinarian_relationship(self, async_session, user_factory, veterinarian_factory, clinic_factory):
        """Test user-veterinarian relationship functionality."""
        # Create veterinarian user
        vet_user = await user_factory.create_veterinarian(async_session)
        clinic = await clinic_factory.create(async_session)
        
        # Create veterinarian profile
        veterinarian = await veterinarian_factory.create(
            async_session, 
            user=vet_user, 
            clinic=clinic
        )
        
        # Test relationship access
        await async_session.refresh(vet_user, ["veterinarian"])
        assert vet_user.veterinarian is not None
        assert vet_user.veterinarian.id == veterinarian.id
        
        # Test reverse relationship
        assert veterinarian.user == vet_user
    
    def test_user_validation_edge_cases(self):
        """Test edge cases and validation scenarios."""
        # Test with minimal required fields
        user = User(
            clerk_user_id="clerk_minimal",
            email="minimal@example.com",
            first_name="Min",
            last_name="User"
        )
        assert user.full_name == "Min User"
        assert user.display_name == "Min User"
        
        # Test with empty names
        user_empty = User(
            clerk_user_id="clerk_empty",
            email="empty@example.com",
            first_name="",
            last_name=""
        )
        assert user_empty.full_name == ""
        assert user_empty.display_name == "empty"  # Should use email prefix
        
        # Test with whitespace names
        user_whitespace = User(
            clerk_user_id="clerk_whitespace",
            email="whitespace@example.com",
            first_name="  John  ",
            last_name="  Doe  "
        )
        assert user_whitespace.full_name == "  John    Doe  "  # Preserves whitespace
    
    def test_user_preferences_edge_cases(self):
        """Test edge cases for user preferences."""
        user = User(
            clerk_user_id="clerk_prefs",
            email="prefs@example.com",
            first_name="Prefs",
            last_name="User"
        )
        
        # Test with None preferences
        assert user.preferences is None
        assert user.get_preference("theme") is None
        assert user.get_preference("theme", "default") == "default"
        
        # Test setting first preference
        user.set_preference("theme", "dark")
        assert user.preferences == {"theme": "dark"}
        
        # Test overwriting preference
        user.set_preference("theme", "light")
        assert user.preferences == {"theme": "light"}
        
        # Test complex preference values
        user.set_preference("settings", {"notifications": True, "language": "en"})
        assert user.get_preference("settings") == {"notifications": True, "language": "en"}
        
        # Test None value preference
        user.set_preference("nullable", None)
        assert user.get_preference("nullable") is None
    
    def test_user_profile_update_edge_cases(self):
        """Test edge cases for profile updates."""
        user = User(
            clerk_user_id="clerk_update",
            email="update@example.com",
            first_name="Update",
            last_name="User"
        )
        
        # Test updating with None values
        user.update_profile(phone_number=None, city=None)
        assert user.phone_number is None
        assert user.city is None
        
        # Test updating with empty strings
        user.update_profile(bio="", address_line2="")
        assert user.bio == ""
        assert user.address_line2 == ""
        
        # Test updating boolean fields
        user.update_profile(email_notifications=False, sms_notifications=True)
        assert user.email_notifications is False
        assert user.sms_notifications is True
        
        # Test invalid field names
        with pytest.raises(ValueError, match="Invalid profile field"):
            user.update_profile(invalid_field="value")
        
        with pytest.raises(ValueError, match="Invalid profile field"):
            user.update_profile(email="newemail@example.com")  # Email not allowed in profile update
    
    def test_user_role_hierarchy_edge_cases(self):
        """Test edge cases for role hierarchy and permissions."""
        # Test with inactive user
        user = User(
            clerk_user_id="clerk_inactive",
            email="inactive@example.com",
            first_name="Inactive",
            last_name="User",
            role=UserRole.PLATFORM_ADMIN,
            status=UserStatus.INACTIVE
        )
        
        # Inactive user should not have access to anything
        assert not user.can_access_role(UserRole.PET_OWNER)
        assert not user.can_access_role(UserRole.PLATFORM_ADMIN)
        
        # Test with suspended user
        user.status = UserStatus.SUSPENDED
        assert not user.can_access_role(UserRole.PET_OWNER)
        
        # Test with pending verification user
        user.status = UserStatus.PENDING_VERIFICATION
        assert not user.can_access_role(UserRole.PET_OWNER)
        
        # Test role hierarchy boundaries
        user.status = UserStatus.ACTIVE
        user.role = UserRole.VET_TECH
        assert user.can_access_role(UserRole.PET_OWNER)
        assert user.can_access_role(UserRole.VET_TECH)
        assert not user.can_access_role(UserRole.VETERINARIAN)
    
    def test_user_status_transitions(self):
        """Test user status transition methods."""
        user = User(
            clerk_user_id="clerk_status",
            email="status@example.com",
            first_name="Status",
            last_name="User",
            status=UserStatus.PENDING_VERIFICATION
        )
        
        # Test activation
        user.activate()
        assert user.status == UserStatus.ACTIVE
        assert user.is_active
        
        # Test deactivation
        user.deactivate()
        assert user.status == UserStatus.INACTIVE
        assert not user.is_active
        
        # Test suspension
        user.suspend()
        assert user.status == UserStatus.SUSPENDED
        assert not user.is_active
        
        # Test reactivation after suspension
        user.activate()
        assert user.status == UserStatus.ACTIVE
        assert user.is_active
    
    def test_user_verification_edge_cases(self):
        """Test edge cases for user verification."""
        user = User(
            clerk_user_id="clerk_verify",
            email="verify@example.com",
            first_name="Verify",
            last_name="User",
            status=UserStatus.PENDING_VERIFICATION,
            email_verified=False,
            phone_verified=False
        )
        
        # Test email verification activates pending user
        assert not user.is_verified
        assert not user.is_active
        
        user.verify_email()
        assert user.email_verified
        assert user.is_verified
        assert user.status == UserStatus.ACTIVE
        assert user.is_active
        
        # Test phone verification doesn't change status if already active
        user.verify_phone()
        assert user.phone_verified
        assert user.status == UserStatus.ACTIVE
        
        # Test verification on already active user
        user2 = User(
            clerk_user_id="clerk_verify2",
            email="verify2@example.com",
            first_name="Verify2",
            last_name="User",
            status=UserStatus.ACTIVE,
            email_verified=False
        )
        
        user2.verify_email()
        assert user2.email_verified
        assert user2.status == UserStatus.ACTIVE  # Should remain active
    
    def test_user_complete_profile_edge_cases(self):
        """Test edge cases for complete profile checking."""
        user = User(
            clerk_user_id="clerk_complete",
            email="complete@example.com",
            first_name="Complete",
            last_name="User"
        )
        
        # Missing phone number
        assert not user.has_complete_profile
        
        # Add phone number
        user.phone_number = "+1234567890"
        assert user.has_complete_profile
        
        # Test with empty phone number
        user.phone_number = ""
        assert not user.has_complete_profile
        
        # Test with whitespace phone number
        user.phone_number = "   "
        assert not user.has_complete_profile
        
        # Test with None values for required fields
        user.phone_number = "+1234567890"
        user.first_name = None
        # This would typically be caught by database constraints
        # but we test the property logic
        assert not user.has_complete_profile


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