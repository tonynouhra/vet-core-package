"""
Tests for User Pydantic schemas.

This module contains comprehensive tests for User schema validation,
including create, update, and response schemas with various edge cases.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.vet_core.models.user import UserRole, UserStatus
from src.vet_core.schemas.user import (
    PetOwnerCreate,
    UserAdminResponse,
    UserCreate,
    UserListResponse,
    UserPreferencesUpdate,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
    VeterinarianCreate,
)


class TestUserCreate:
    """Test UserCreate schema validation."""

    def test_valid_user_create(self):
        """Test creating a valid user."""
        user_data = {
            "clerk_user_id": "user_123abc",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "1234567890",
            "role": UserRole.PET_OWNER,
        }

        user = UserCreate(**user_data)
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.phone_number == "(123) 456-7890"  # Formatted
        assert user.role == UserRole.PET_OWNER
        assert user.country == "US"  # Default value
        assert user.email_notifications is True  # Default value
        assert user.sms_notifications is False  # Default value

    def test_email_validation(self):
        """Test email validation."""
        base_data = {
            "clerk_user_id": "user_123abc",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Valid email
        user = UserCreate(email="test@example.com", **base_data)
        assert user.email == "test@example.com"

        # Email converted to lowercase
        user = UserCreate(email="TEST@EXAMPLE.COM", **base_data)
        assert user.email == "test@example.com"

        # Invalid emails
        with pytest.raises(ValidationError):
            UserCreate(email="invalid-email", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(email="test..test@example.com", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(email=".test@example.com", **base_data)

    def test_phone_number_validation(self):
        """Test phone number validation and formatting."""
        base_data = {
            "clerk_user_id": "user_123abc",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        # US 10-digit number
        user = UserCreate(phone_number="1234567890", **base_data)
        assert user.phone_number == "(123) 456-7890"

        # US 11-digit number with country code
        user = UserCreate(phone_number="11234567890", **base_data)
        assert user.phone_number == "+1 (123) 456-7890"

        # International number
        user = UserCreate(phone_number="441234567890", **base_data)
        assert user.phone_number == "+441234567890"

        # With formatting characters
        user = UserCreate(phone_number="(123) 456-7890", **base_data)
        assert user.phone_number == "(123) 456-7890"

        # Invalid phone numbers
        with pytest.raises(ValidationError):
            UserCreate(phone_number="123", **base_data)  # Too short

        with pytest.raises(ValidationError):
            UserCreate(phone_number="12345678901234567890", **base_data)  # Too long

    def test_name_validation(self):
        """Test name field validation."""
        base_data = {"clerk_user_id": "user_123abc", "email": "test@example.com"}

        # Valid names
        user = UserCreate(first_name="john", last_name="doe", **base_data)
        assert user.first_name == "John"
        assert user.last_name == "Doe"

        # Names with hyphens and apostrophes
        user = UserCreate(first_name="mary-jane", last_name="o'connor", **base_data)
        assert user.first_name == "Mary-Jane"
        assert user.last_name == "O'Connor"

        # Invalid names
        with pytest.raises(ValidationError):
            UserCreate(first_name="", last_name="Doe", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(first_name="John123", last_name="Doe", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(first_name="John", last_name="", **base_data)

    def test_clerk_user_id_validation(self):
        """Test Clerk user ID validation."""
        base_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Valid Clerk user ID
        user = UserCreate(clerk_user_id="user_123abc", **base_data)
        assert user.clerk_user_id == "user_123abc"

        # Invalid Clerk user IDs
        with pytest.raises(ValidationError):
            UserCreate(clerk_user_id="", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(clerk_user_id="invalid_format", **base_data)

        with pytest.raises(ValidationError):
            UserCreate(clerk_user_id="user_", **base_data)

    def test_role_validation(self):
        """Test role validation."""
        base_data = {
            "clerk_user_id": "user_123abc",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Valid roles
        for role in UserRole:
            user = UserCreate(role=role, **base_data)
            assert user.role == role

        # Default role
        user = UserCreate(**base_data)
        assert user.role == UserRole.PET_OWNER

    def test_preferences_validation(self):
        """Test preferences validation."""
        base_data = {
            "clerk_user_id": "user_123abc",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Valid preferences
        preferences = {"theme": "dark", "language": "en", "timezone": "UTC"}
        user = UserCreate(preferences=preferences, **base_data)
        assert user.preferences == preferences

        # Invalid preference key
        with pytest.raises(ValidationError):
            UserCreate(preferences={"invalid_key": "value"}, **base_data)

        # Non-dict preferences
        with pytest.raises(ValidationError):
            UserCreate(preferences="invalid", **base_data)


class TestUserUpdate:
    """Test UserUpdate schema validation."""

    def test_valid_user_update(self):
        """Test valid user update."""
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone_number": "9876543210",
        }

        user_update = UserUpdate(**update_data)
        assert user_update.first_name == "Jane"
        assert user_update.last_name == "Smith"
        assert user_update.phone_number == "(987) 654-3210"

    def test_partial_update(self):
        """Test partial user update."""
        # Only update first name
        user_update = UserUpdate(first_name="Jane")
        assert user_update.first_name == "Jane"
        assert user_update.last_name is None

        # Only update preferences
        preferences = {"theme": "light"}
        user_update = UserUpdate(preferences=preferences)
        assert user_update.preferences == preferences

    def test_empty_update_validation(self):
        """Test that empty update is rejected."""
        with pytest.raises(ValidationError):
            UserUpdate()

    def test_update_field_validation(self):
        """Test that update fields use same validation as create."""
        # Invalid phone number
        with pytest.raises(ValidationError):
            UserUpdate(phone_number="123")

        # Invalid name
        with pytest.raises(ValidationError):
            UserUpdate(first_name="")


class TestUserResponse:
    """Test UserResponse schema."""

    def test_user_response_creation(self):
        """Test creating user response from model data."""
        user_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.PET_OWNER,
            "status": UserStatus.ACTIVE,
            "email_notifications": True,
            "sms_notifications": False,
            "email_verified": True,
            "phone_verified": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        response = UserResponse(**user_data)
        assert response.id == user_data["id"]
        assert response.email == user_data["email"]
        assert response.role == UserRole.PET_OWNER
        assert response.status == UserStatus.ACTIVE


class TestUserAdminResponse:
    """Test UserAdminResponse schema."""

    def test_admin_response_includes_sensitive_fields(self):
        """Test that admin response includes sensitive fields."""
        user_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.PET_OWNER,
            "status": UserStatus.ACTIVE,
            "clerk_user_id": "user_123abc",
            "email_notifications": True,
            "sms_notifications": False,
            "email_verified": True,
            "phone_verified": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        response = UserAdminResponse(**user_data)
        assert response.clerk_user_id == "user_123abc"
        assert hasattr(response, "terms_accepted_at")
        assert hasattr(response, "privacy_accepted_at")


class TestRoleSpecificSchemas:
    """Test role-specific user creation schemas."""

    def test_pet_owner_create(self):
        """Test PetOwnerCreate schema."""
        user_data = {
            "clerk_user_id": "user_123abc",
            "email": "owner@example.com",
            "first_name": "Pet",
            "last_name": "Owner",
        }

        pet_owner = PetOwnerCreate(**user_data)
        assert pet_owner.role == UserRole.PET_OWNER

    def test_veterinarian_create(self):
        """Test VeterinarianCreate schema."""
        user_data = {
            "clerk_user_id": "user_123abc",
            "email": "vet@example.com",
            "first_name": "Dr.",
            "last_name": "Smith",
        }

        vet = VeterinarianCreate(**user_data)
        assert vet.role == UserRole.VETERINARIAN


class TestUserRoleUpdate:
    """Test UserRoleUpdate schema."""

    def test_valid_role_update(self):
        """Test valid role update."""
        for role in UserRole:
            role_update = UserRoleUpdate(role=role)
            assert role_update.role == role


class TestUserStatusUpdate:
    """Test UserStatusUpdate schema."""

    def test_valid_status_update(self):
        """Test valid status update."""
        for status in UserStatus:
            status_update = UserStatusUpdate(status=status)
            assert status_update.status == status


class TestUserPreferencesUpdate:
    """Test UserPreferencesUpdate schema."""

    def test_valid_preferences_update(self):
        """Test valid preferences update."""
        preferences = {"theme": "dark", "language": "en", "timezone": "UTC"}

        pref_update = UserPreferencesUpdate(preferences=preferences)
        assert pref_update.preferences == preferences

    def test_invalid_preferences_update(self):
        """Test invalid preferences update."""
        with pytest.raises(ValidationError):
            UserPreferencesUpdate(preferences={"invalid_key": "value"})
