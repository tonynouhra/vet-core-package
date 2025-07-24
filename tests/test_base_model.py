"""
Tests for the base model functionality.
"""

import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.vet_core.models.base import Base, BaseModel


class TestModel(BaseModel):
    """Test model for testing base functionality."""

    __tablename__ = "test_model"


class TestBaseModel:
    """Test cases for BaseModel functionality."""

    def test_base_model_creation(self):
        """Test that BaseModel can be instantiated with proper fields."""
        model = TestModel()

        # Check that all required fields exist
        assert hasattr(model, "id")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert hasattr(model, "created_by")
        assert hasattr(model, "updated_by")
        assert hasattr(model, "deleted_at")
        assert hasattr(model, "is_deleted")

        # Check default values
        assert model.is_deleted is False
        assert model.deleted_at is None
        assert model.created_by is None
        assert model.updated_by is None

    def test_model_repr(self):
        """Test string representation of model."""
        model = TestModel()
        model.id = uuid.uuid4()

        repr_str = repr(model)
        assert "TestModel" in repr_str
        assert str(model.id) in repr_str

    def test_to_dict(self):
        """Test conversion to dictionary."""
        model = TestModel()
        model.id = uuid.uuid4()
        model.created_at = datetime.utcnow()
        model.updated_at = datetime.utcnow()

        result = model.to_dict()

        assert isinstance(result, dict)
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "is_deleted" in result

        # Check UUID is converted to string
        assert isinstance(result["id"], str)
        # Check datetime is converted to ISO format
        assert isinstance(result["created_at"], str)

    def test_to_dict_exclude_deleted(self):
        """Test to_dict excludes deleted records when requested."""
        model = TestModel()
        model.is_deleted = True

        result = model.to_dict(exclude_deleted=True)
        assert result == {}

        result = model.to_dict(exclude_deleted=False)
        assert isinstance(result, dict)
        assert result["is_deleted"] is True

    def test_soft_delete(self):
        """Test soft delete functionality."""
        model = TestModel()
        user_id = uuid.uuid4()

        assert model.is_deleted is False
        assert model.deleted_at is None

        model.soft_delete(deleted_by=user_id)

        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert model.updated_by == user_id
        assert isinstance(model.deleted_at, datetime)

    def test_restore(self):
        """Test restore functionality."""
        model = TestModel()
        user_id = uuid.uuid4()

        # First soft delete
        model.soft_delete()
        assert model.is_deleted is True
        assert model.deleted_at is not None

        # Then restore
        model.restore(restored_by=user_id)

        assert model.is_deleted is False
        assert model.deleted_at is None
        assert model.updated_by == user_id

    def test_update_fields(self):
        """Test update_fields functionality."""
        model = TestModel()
        user_id = uuid.uuid4()

        model.update_fields(created_by=user_id, is_deleted=True)

        assert model.created_by == user_id
        assert model.is_deleted is True

    def test_update_fields_invalid_attribute(self):
        """Test update_fields with invalid attribute raises error."""
        model = TestModel()

        with pytest.raises(AttributeError):
            model.update_fields(invalid_field="value")

    def test_get_table_name(self):
        """Test get_table_name class method."""
        assert TestModel.get_table_name() == "test_model"

    def test_get_primary_key_column(self):
        """Test get_primary_key_column class method."""
        assert TestModel.get_primary_key_column() == "id"

    def test_create_query_filter_active(self):
        """Test create_query_filter_active class method."""
        filter_clause = TestModel.create_query_filter_active()
        # This would normally be used in SQLAlchemy queries
        assert filter_clause is not None

    def test_create_query_filter_deleted(self):
        """Test create_query_filter_deleted class method."""
        filter_clause = TestModel.create_query_filter_deleted()
        # This would normally be used in SQLAlchemy queries
        assert filter_clause is not None


class TestBase:
    """Test cases for Base declarative base."""

    def test_base_exists(self):
        """Test that Base class exists and can be used."""
        assert Base is not None
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_uuid_type_annotation(self):
        """Test that UUID type annotation is properly configured."""
        assert hasattr(Base, "type_annotation_map")
        assert uuid.UUID in Base.type_annotation_map
